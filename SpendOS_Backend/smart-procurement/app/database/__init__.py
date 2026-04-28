"""
Async database session management using SQLAlchemy.
"""

import ssl

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()

# Database setup — Neon DB (and most cloud providers) require SSL
_connect_args: dict = {}
if "neon.tech" in settings.database_url:
    # Create a proper SSL context for Neon DB
    ssl_context = ssl.create_default_context()
    _connect_args["ssl"] = ssl_context

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise



