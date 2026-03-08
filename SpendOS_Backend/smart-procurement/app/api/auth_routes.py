"""
Auth Routes — DB-backed user registration and login.
POST /api/auth/register — register a new user
POST /api/auth/token    — obtain a JWT access token
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_password_hash, verify_password, create_access_token
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)


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
    
    # Security: In production (Vercel + Render), we need Secure and SameSite=None
    # for cookies to work across different domains.
    cookie_secure = not settings.debug
    cookie_samesite = "none" if not settings.debug else "lax"
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=1440 * 60, # 24 hours
    )

    return {"user": {"email": user.email, "full_name": user.full_name}}


@router.post("/logout")
async def logout(response: Response):
    """Clear the HTTPOnly cookie."""
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out"}
