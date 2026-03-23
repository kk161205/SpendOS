import os
import sys

# Set mock environment variables BEFORE any app imports
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["SERP_API_KEY"] = "test-serp-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Adjust DATABASE_URL to use a test database if not already one
# We don't hardcode credentials here anymore; we rely on the environment/settings
# but override the DB name to avoid wiping production data.
from app.config import get_settings
try:
    current_url = get_settings().database_url
    if "_test" not in current_url:
        # Simple suffix replacement for common postgres URLs
        if "/" in current_url:
            base, db_name = current_url.rsplit("/", 1)
            os.environ["DATABASE_URL"] = f"{base}/{db_name}_test"
except Exception:
    # Fallback default if settings fail to load
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:root@localhost:5432/smart_procurement_test"

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

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
            # Dropping first ensures we catch schema changes (e.g. new columns)
            # NOT suitable for production, but essential for consistent tests.
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Fallback to the main DB if the test DB doesn't exist, 
        # but this is risky as it might wipe data.
        pass
    
    return engine

@pytest_asyncio.fixture(scope="session")
async def db_session(test_engine):
    """Yield a database session for each test case."""
    session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture(scope="session")
async def client(db_session):
    """Yield an AsyncClient for FastAPI testing."""
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

@pytest_asyncio.fixture(scope="session")
async def authenticated_client(client: AsyncClient):
    """Register a test user and ensure the client has the auth cookie and headers."""
    import time
    timestamp = int(time.time() * 1000)
    email = f"test{timestamp}@example.com"
    password = "StrongP@ss123!" # Added ! for complexity if needed
    
    # 1. Register
    await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    
    # 2. Login
    resp = await client.post("/api/auth/token", data={
        "username": email,
        "password": password,
    })
    
    # Extract cookies/headers
    token = resp.cookies.get("access_token")
    if token:
        client.headers.update({"Authorization": token.strip('"')})
        
    csrf = resp.cookies.get("csrf_token")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf.strip('"')})
    
    return client
