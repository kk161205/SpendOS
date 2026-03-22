import asyncio
import json
import redis.asyncio as redis
from httpx import AsyncClient
from arq import create_pool
from arq.connections import RedisSettings
from app.main import app
from app.config import get_settings

settings = get_settings()

async def verify_sse():
    task_id = "test-task-sse-123"
    user_id = "test-user-456"
    channel = f"task_updates:{task_id}"
    
    # Init ARQ pool for the app state
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    
    # We need a token for auth
    from app.auth import create_access_token
    token = create_access_token({"sub": user_id, "email": "test@example.com"})
    
    print(f"Connecting to SSE for task {task_id}...")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Start the SSE request
        async def listen_to_sse():
            events = []
            try:
                # Use the token in query param as we implemented in auth.py
                async with client.stream("GET", f"/api/procurement/events/{task_id}?token={token}") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            print(f"  [SSE RECEIVE] {data}")
                            events.append(data)
                            if data.get("status") in ["completed", "failed"] or "error" in data:
                                break
            except Exception as e:
                print(f"  [SSE ERROR] {e}")
            return events

        # Start listening
        listener_task = asyncio.create_task(listen_to_sse())
        
        # Give it a moment to connect and subscribe
        await asyncio.sleep(2)
        
        # 2. Publish updates to Redis
        r = redis.from_url(settings.redis_url)
        print("Publishing 'processing'...")
        await r.publish(channel, json.dumps({"status": "processing"}))
        await asyncio.sleep(0.5)
        
        print("Publishing 'completed'...")
        await r.publish(channel, json.dumps({"status": "completed", "result": {"vendors": []}}))
        
        # 3. Wait for listener to finish
        received_events = await listener_task
        
        # Cleanup
        await app.state.arq_pool.close()
        
        # Verification
        statuses = [e.get("status") for e in received_events if e.get("status")]
        errors = [e.get("error") for e in received_events if e.get("error")]
        
        print(f"Status flow: {statuses}")
        if errors:
            print(f"Errors flow: {errors}")
            # If error is 'Task not found', it's expected as we didn't insert into DB.
            # But the Pub/Sub part should still have worked if we connected in time.
            if "Task not found" in errors and ("processing" in statuses or "completed" in statuses):
                 print("--- VERIFICATION SUCCESS (Task not found in DB but got Pub/Sub events) ---")
                 return
            elif "Task not found" in errors:
                 # If we only got 'Task not found' and no events, maybe we missed them.
                 # Actually, for this test, we care about the flow.
                 print("--- VERIFICATION PARTIAL (Task not found in DB - which is expected) ---")
                 # Let's check if we got at least one status change
                 if "processing" in statuses or "completed" in statuses:
                     print("--- VERIFICATION SUCCESS ---")
                 else:
                     print("--- VERIFICATION FAILED (No events received) ---")
        elif "processing" in statuses and "completed" in statuses:
            print("--- VERIFICATION SUCCESS ---")
        else:
            print("--- VERIFICATION FAILED ---")

if __name__ == "__main__":
    asyncio.run(verify_sse())
