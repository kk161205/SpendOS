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

@app.get("/api/procurement/status/mock-task-123")
async def get_status():
    # This might be used by the UI instead of SSE in some cases
    return {
        "task_id": "mock-task-123",
        "status": "completed",
        "result": {
            "ranked_vendors": [
                {
                    "vendor_id": "v1",
                    "vendor_name": "Mock Vendor A",
                    "final_score": 95,
                    "risk_score": 10,
                    "reliability_score": 90,
                    "cost_score": 92,
                    "rank": 1,
                    "risk_reasoning": "Great track record."
                }
            ],
            "ai_explanation": "Vendor A is the best.",
            "product_category": "Electronics"
        }
    }

@app.get("/api/procurement/events/{task_id}")
async def stream_events(task_id: str, token: str = None):
    async def event_generator():
        # Initial state
        yield f"data: {json.dumps({'status': 'processing'})}\n\n"
        await asyncio.sleep(1)
        
        # Final result
        result = {
            "status": "completed",
            "result": {
                "id": "session-123",
                "product_name": "Mock Item",
                "category": "Electronics",
                "results": {
                    "ranked_vendors": [
                        {
                            "vendor_id": "v1",
                            "vendor_name": "Mock Vendor A",
                            "final_score": 95.5,
                            "reliability_score": 98.0,
                            "risk_score": 5.0,
                            "cost_score": 92.0,
                            "rank": 1,
                            "explanation": "Excellent choice"
                        },
                        {
                            "vendor_id": "v2",
                            "vendor_name": "Mock Vendor B",
                            "final_score": 88.2,
                            "reliability_score": 85.0,
                            "risk_score": 15.0,
                            "cost_score": 98.0,
                            "rank": 2,
                            "explanation": "Good budget option"
                        }
                    ],
                    "total_vendors_evaluated": 2,
                    "ai_explanation": "Vendor A is highly recommended due to superior reliability.",
                    "product_category": "Electronics"
                }
            }
        }
        yield f"data: {json.dumps(result)}\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/procurement/export/{session_id}")
async def export_results(session_id: str):
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Procurement Analysis Report"])
    writer.writerow(["Product", "Mock Item"])
    writer.writerow([])
    writer.writerow(["Rank", "Vendor", "Score"])
    writer.writerow([1, "Mock Vendor A", 95])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=mock_results_{session_id}.csv"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

