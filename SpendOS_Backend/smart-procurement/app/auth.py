"""
JWT Authentication utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from jwt.exceptions import PyJWTError as JWTError
from fastapi import Depends, HTTPException, status, Request
from app.config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency — decode JWT from HttpOnly cookie or Authorization header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    # 1. Try Cookie
    token = request.cookies.get("access_token")
    
    # 2. Try Authorization Header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.strip('"')

    if not token:
        raise credentials_exception

    # Handle Bearer prefix
    if token.startswith("Bearer "):
        try:
            token = token.split(" ")[1]
        except IndexError:
            raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id, "email": payload.get("email")}
    except JWTError:
        raise credentials_exception
