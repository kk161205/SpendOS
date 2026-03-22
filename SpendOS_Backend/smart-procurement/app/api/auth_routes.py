"""
Auth Routes — DB-backed user registration and login.
POST /api/auth/register — register a new user
POST /api/auth/token    — obtain a JWT access token
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_password_hash, verify_password, create_access_token, create_refresh_token, verify_refresh_token
from app.database import get_db
from app.config import get_settings
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])
settings = get_settings()


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if all(c.isalnum() for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class TokenResponse(BaseModel):
    user: dict


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account (stored in PostgreSQL)."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    await db.flush()

    return {"message": "User registered successfully", "user_id": user.id}


@router.post("/token", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange credentials for a JWT access token.
    In Swagger Authorize dialog: put your EMAIL in the 'username' field.
    Leave client_id and client_secret blank.
    """
    email = form_data.username  # Swagger sends email as 'username'

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": user.id, "email": user.email, "full_name": user.full_name}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "email": user.email, "full_name": user.full_name}
    )
    
    # Security: In production (Vercel + Render), we need Secure and SameSite=None
    # for cookies to work across different domains.
    cookie_secure = not settings.debug
    cookie_samesite = "none" if not settings.debug else "lax"
    csrf_token = secrets.token_urlsafe(32)
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Frontend JS must read this to send as X-CSRF-Token
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )

    return {"user": {"email": user.email, "full_name": user.full_name}}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using a valid HttpOnly refresh_token cookie."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    payload = verify_refresh_token(token)
    
    user_id = payload.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
        
    new_access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "full_name": user.full_name}
    )
    csrf_token = secrets.token_urlsafe(32)
    
    cookie_secure = not settings.debug
    cookie_samesite = "none" if not settings.debug else "lax"
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    
    return {"user": {"email": user.email, "full_name": user.full_name}}


@router.post("/logout")
async def logout(response: Response):
    """Clear auth and CSRF cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    response.delete_cookie("refresh_token")
    return {"message": "Successfully logged out"}
