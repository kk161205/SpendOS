import asyncio
from arq.worker import run_worker
from app.worker import WorkerSettings

if __name__ == '__main__':
    # Fix for Python 3.14+ where asyncio.get_event_loop() fails if no loop is set
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        run_worker(WorkerSettings)
    finally:
        loop.close()
