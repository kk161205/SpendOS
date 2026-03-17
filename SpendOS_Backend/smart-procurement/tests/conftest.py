import asyncio
import pytest
import pytest_asyncio
from app.database import init_db, engine

@pytest.fixture(scope="session")
def event_loop():
    """Override the default event_loop fixture to be session-scoped."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db(event_loop):
    """Initialize the database once for the entire test session."""
    await init_db()
    yield
    await engine.dispose()
