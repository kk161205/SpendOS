import secrets
import logging
from fastapi import HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_password_hash, verify_password, create_access_token, create_refresh_token, verify_refresh_token
from app.models.user import User
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AuthService:
    @staticmethod
    async def register(payload, db: AsyncSession):
        """Register a new user account."""
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
        await db.commit()
        return user.id

    @staticmethod
    async def login(response: Response, form_data, db: AsyncSession):
        """Exchange credentials for the access/refresh cookie set."""
        email = form_data.username
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
        
        csrf_token = secrets.token_urlsafe(32)
        cookie_secure = not settings.debug
        cookie_samesite = "none" if not settings.debug else "lax"
        
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
            httponly=False,
            samesite=cookie_samesite,
            secure=cookie_secure,
            max_age=settings.access_token_expire_minutes * 60,
        )
        return user, csrf_token

    @staticmethod
    async def refresh_session(request: Request, response: Response, db: AsyncSession):
        """Obtain a new access token via the refresh cookie."""
        token = request.cookies.get("refresh_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
        
        payload = verify_refresh_token(token)
        user_id = payload.get("user_id")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
            
        new_token = create_access_token(
            data={"sub": user.id, "email": user.email, "full_name": user.full_name}
        )
        csrf_token = secrets.token_urlsafe(32)
        
        cookie_secure = not settings.debug
        cookie_samesite = "none" if not settings.debug else "lax"
        
        response.set_cookie(
            key="access_token", value=f"Bearer {new_token}",
            httponly=True, samesite=cookie_samesite, secure=cookie_secure,
            max_age=settings.access_token_expire_minutes * 60,
        )
        response.set_cookie(
            key="csrf_token", value=csrf_token,
            httponly=False, samesite=cookie_samesite, secure=cookie_secure,
            max_age=settings.access_token_expire_minutes * 60,
        )
        return user, csrf_token
