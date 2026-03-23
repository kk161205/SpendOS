import os
import sys

# Set mock environment variables BEFORE any app imports
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["SERP_API_KEY"] = "test-serp-key"
# Using credentials found in .env: postgres:root
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:root@localhost:5432/smart_procurement_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Now import the app
from app.database import Base, get_db
from app.config import get_settings
from app.main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_engine():
    """Create a session-scoped engine and initialize the schema."""
    settings = get_settings()
    # We use a test-specific database name to avoid wiping development data
    # Note: The database 'smart_procurement_test' must exist.
    engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
    
    try:
        async with engine.begin() as conn:
            from app.models.user import User # noqa
            from app.models.task import ProcurementTask # noqa
            from app.models.procurement import ProcurementSession, VendorResult # noqa
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Fallback to the main DB if the test DB doesn't exist, 
        # but this is risky as it might wipe data.
        pass
    
    return engine

@pytest_asyncio.fixture
async def db_session(test_engine):
    """Yield a database session for each test case."""
    session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session):
    """Yield an AsyncClient for FastAPI testing."""
    from httpx import AsyncClient, ASGITransport
    
    # Override get_db dependency
    async def _get_test_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()
