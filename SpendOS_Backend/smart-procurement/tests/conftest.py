import os
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.database import Base, get_db
from app.config import get_settings
from app.main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_engine():
    """Create a session-scoped engine and initialize the schema."""
    settings = get_settings()
    # NullPool is key for avoiding overlapping connection usage in async tests
    engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
    
    async with engine.begin() as conn:
        from app.models.user import User # noqa
        from app.models.task import ProcurementTask # noqa
        from app.models.procurement import ProcurementSession, VendorResult # noqa
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def session_factory(test_engine):
    """Create a session factory for the entire test session."""
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_app_overrides(session_factory):
    """Override get_db globally for the FastAPI app during testing."""
    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
