"""
Async database session management using SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()

# Database setup
engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        from app.models.user import User  # noqa: F401
        from app.models.task import ProcurementTask  # noqa: F401
        from app.models.procurement import ProcurementSession, VendorResult  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
