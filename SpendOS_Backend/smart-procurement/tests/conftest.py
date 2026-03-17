import asyncio
import pytest
import pytest_asyncio
from app.database import init_db, engine

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Initialize the database once for the entire test session."""
    await init_db()
    yield
    # Cleanup after session if needed
    async with engine.begin() as conn:
        # We don't necessarily want to drop tables in CI if they are reused, 
        # but for a fresh run it's fine.
        pass
