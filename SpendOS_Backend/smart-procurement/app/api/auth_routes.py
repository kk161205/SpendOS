from fastapi import APIRouter, Depends, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])

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
    csrf_token: str | None = None

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account (stored in PostgreSQL)."""
    user_id = await AuthService.register(payload, db)
    return {"message": "User registered successfully", "user_id": user_id}


@router.post("/token", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Obtain access/refresh tokens in HttpOnly cookies."""
    user, csrf_token = await AuthService.login(response, form_data, db)
    return {"user": {"email": user.email, "full_name": user.full_name}, "csrf_token": csrf_token}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using the refresh_token cookie."""
    user, csrf_token = await AuthService.refresh_session(request, response, db)
    return {"user": {"email": user.email, "full_name": user.full_name}, "csrf_token": csrf_token}


@router.post("/logout")
async def logout(response: Response):
    """Clear auth and CSRF cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    response.delete_cookie("refresh_token")
    return {"message": "Successfully logged out"}
