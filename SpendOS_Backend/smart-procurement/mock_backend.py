import asyncio
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "database": "connected", "redis": "connected"}

@app.post("/api/auth/token")
async def login():
    return {"access_token": "mock-token", "token_type": "bearer"}

@app.post("/api/procurement/analyze")
async def analyze():
    return {"task_id": "mock-task-123"}

@app.get("/api/procurement/events/{task_id}")
async def stream_events(task_id: str, token: str = None):
    async def event_generator():
        # Initial state
        yield f"data: {json.dumps({'status': 'processing'})}\n\n"
        await asyncio.sleep(2)
        
        # Intermediate update
        yield f"data: {json.dumps({'status': 'processing', 'progress': 50})}\n\n"
        await asyncio.sleep(2)
        
        # Final result
        result = {
            "status": "completed",
            "result": [
                {
                    "name": "Mock Vendor A",
                    "price": 100,
                    "reliability_score": 90,
                    "risk_score": 10,
                    "final_score": 95,
                    "explanation": "Great choice!"
                }
            ]
        }
        yield f"data: {json.dumps(result)}\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
