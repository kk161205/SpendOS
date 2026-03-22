import asyncio
import csv
import io
import logging
import uuid
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_user
from app.database import get_db
from app.models.task import ProcurementTask
from app.models.procurement import ProcurementSession, VendorResult
from app.schemas.procurement_schema import (
    ProcurementRequest as ProcurementRequestSchema,
    ProcurementAnalysisResponse,
    VendorScoreResponse,
    TaskAcceptedResponse,
    TaskStatusResponse,
    ProcurementHistorySessionResponse,
    ProcurementHistoryPaginatedResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/procurement", tags=["Procurement"])

def generate_procurement_hash(payload: ProcurementRequestSchema) -> str:
    """Generate a deterministic sha256 hash representing unique AI parameters."""
    data_to_hash = {
        "product": payload.product_name.lower().strip(),
        "category": payload.product_category.lower().strip(),
        "budget": payload.budget_usd,
        "constraints": payload.scoring_weights.model_dump()
    }
    hasher = hashlib.sha256()
    hasher.update(json.dumps(data_to_hash, sort_keys=True).encode("utf-8"))
    return f"procurement_cache:{hasher.hexdigest()}"


@router.post("/analyze", response_model=TaskAcceptedResponse)
async def analyze_procurement(
    payload: ProcurementRequestSchema,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a background task to execute the full AI procurement pipeline.
    Returns immediately with a task_id.

    The task is enqueued to ARQ (Redis-backed) for reliable, retryable execution
    in a separate worker process.
    """
    logger.info(f"[/analyze] Received analysis request for '{payload.product_name}' by user '{current_user['user_id']}'")
    logger.debug(f"[/analyze] Payload: {payload.model_dump()}")

    request_id = str(uuid.uuid4())
    arq_pool = request.app.state.arq_pool

    # Caching Layer Check
    cache_key = generate_procurement_hash(payload)
    cached_result_bytes = await arq_pool.get(cache_key)

    if cached_result_bytes:
        logger.info(f"[/analyze] CACHE HIT for '{payload.product_name}'. Bypassing background worker.")
        cached_result = json.loads(cached_result_bytes.decode("utf-8"))
        cached_result["request_id"] = request_id  # Emulate unique request structure
        
        # Deposit directly as "completed" to save cost/latency
        task = ProcurementTask(id=request_id, user_id=current_user["user_id"], status="completed", result=cached_result)
        db.add(task)
        await db.commit()
        
        # The frontend still receives "pending" to emulate async resolution polling gracefully
        return TaskAcceptedResponse(task_id=request_id, status="pending")

    # Cache Miss -> Queue to worker
    task = ProcurementTask(id=request_id, user_id=current_user["user_id"], status="pending")
    db.add(task)
    await db.commit()

    logger.info(f"[/analyze] Created ProcurementTask with ID: {request_id}. Enqueuing to ARQ.")
    await arq_pool.enqueue_job(
        "run_procurement_task",
        task_id=request_id,
        payload=payload.model_dump(),
        user_id=current_user["user_id"],
    )

    return TaskAcceptedResponse(task_id=request_id, status="pending")


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status and result of a background procurement analysis task.
    """
    result = await db.execute(
        select(ProcurementTask).where(
            ProcurementTask.id == task_id,
            ProcurementTask.user_id == current_user["user_id"]
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        result=task.result if task.status == "completed" else None
    )


async def task_event_generator(task_id: str, user_id: str, request: Request, db_factory):
    """
    Subscribes to Redis Pub/Sub for a specific task and yields SSE events.
    """
    arq_pool = request.app.state.arq_pool
    
    # 1. Yield current state from DB immediately
    async with db_factory() as db:
        result = await db.execute(
            select(ProcurementTask).where(
                ProcurementTask.id == task_id,
                ProcurementTask.user_id == user_id
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
            return
            
        yield f"data: {json.dumps({'status': task.status, 'result': task.result})}\n\n"
        
        if task.status in ["completed", "failed"]:
            return

    # 2. Subscribe to Redis for future updates
    pubsub = arq_pool.pubsub()
    await pubsub.subscribe(f"task_updates:{task_id}")
    
    try:
        # We use a timeout to occasionally check if the connection is still alive
        while True:
            message = await pubsub.get_message(ignore_subscribe_message=True, timeout=1.0)
            if message:
                data_str = message["data"]
                if isinstance(data_str, bytes):
                    data_str = data_str.decode("utf-8")
                data = json.loads(data_str)
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in ["completed", "failed"]:
                    break
            
            # Check if task finished while we were setting up subscription
            # (Edge case protection)
            async with db_factory() as db:
                check_result = await db.execute(
                    select(ProcurementTask.status).where(ProcurementTask.id == task_id)
                )
                current_status = check_result.scalar_one_or_none()
                if current_status in ["completed", "failed"]:
                    # Final check: did we miss the message? 
                    # If we don't have the result yet, fetch it.
                    final_result = await db.execute(
                        select(ProcurementTask).where(ProcurementTask.id == task_id)
                    )
                    final_task = final_result.scalar_one_or_none()
                    yield f"data: {json.dumps({'status': final_task.status, 'result': final_task.result if final_task.status == 'completed' else None})}\n\n"
                    break
                    
            await asyncio.sleep(0.1) # Prevent tight loop if get_message is instant
    except Exception as e:
        logger.error(f"SSE stream error for task {task_id}: {e}")
        yield f"data: {json.dumps({'error': 'Stream encountered an error'})}\n\n"
    finally:
        await pubsub.unsubscribe(f"task_updates:{task_id}")


@router.get("/events/{task_id}")
async def stream_task_events(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    SSE endpoint to stream real-time task status updates.
    """
    from app.database import async_session_factory
    
    return StreamingResponse(
        task_event_generator(task_id, current_user["user_id"], request, async_session_factory),
        media_type="text/event-stream"
    )


@router.get("/history", response_model=ProcurementHistoryPaginatedResponse)
async def get_procurement_history(
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all past procurement sessions with their top vendors for the current user.
    """
    from sqlalchemy.orm import selectinload
    from sqlalchemy import func

    count_stmt = select(func.count(ProcurementSession.id)).where(
        ProcurementSession.user_id == current_user["user_id"]
    )
    total_count = await db.scalar(count_stmt)

    result = await db.execute(
        select(ProcurementSession)
        .where(ProcurementSession.user_id == current_user["user_id"])
        .order_by(ProcurementSession.created_at.desc())
        .options(selectinload(ProcurementSession.vendor_results))
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()

    response = []
    for s in sessions:
        # Sort vendors by rank
        sorted_vendors = sorted(s.vendor_results, key=lambda v: v.rank)
        
        # Build results object that mimics ProcurementAnalysisResponse for the UI
        vendor_dicts = []
        for v in sorted_vendors:
            vendor_dicts.append({
                "vendor_id": v.vendor_id or v.id,
                "vendor_name": v.vendor_name,
                "final_score": v.final_score,
                "risk_score": v.risk_score,
                "reliability_score": v.reliability_score,
                "cost_score": v.cost_score,
                "rank": v.rank,
                "risk_reasoning": v.explanation,
            })
            
        results_obj = {
            "ranked_vendors": vendor_dicts,
            "total_vendors_evaluated": len(vendor_dicts),
            "ai_explanation": s.ai_explanation,
            "product_category": s.category,
        }
        
        response.append(ProcurementHistorySessionResponse(
            id=s.id,
            timestamp=s.created_at.isoformat(),
            product_name=s.product_name,
            category=s.category,
            status=s.status,
            results=results_obj,
        ))

    return ProcurementHistoryPaginatedResponse(total=total_count, items=response)


@router.delete("/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procurement_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific procurement session.
    Cascades automatically to VendorResult due to SQLAlchemy relationship.
    """
    result = await db.execute(
        select(ProcurementSession).where(
            ProcurementSession.id == session_id,
            ProcurementSession.user_id == current_user["user_id"]
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found or forbidden"
        )
        
    await db.delete(session)
    await db.commit()
    return None


@router.get("/export/{session_id}")
async def export_procurement_results(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export procurement results as a CSV file.
    Only accessible by the owner of the session.
    """
    from sqlalchemy.orm import selectinload
    
    # 1. Fetch the session and its results
    result = await db.execute(
        select(ProcurementSession)
        .where(
            ProcurementSession.id == session_id,
            ProcurementSession.user_id == current_user["user_id"]
        )
        .options(selectinload(ProcurementSession.vendor_results))
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found or access denied"
        )
    
    # 2. Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers - Session Metadata
    writer.writerow(["Procurement Analysis Report"])
    writer.writerow(["Product Name", session.product_name])
    writer.writerow(["Category", session.category])
    writer.writerow(["Budget (USD)", session.budget or "N/A"])
    writer.writerow(["Date", session.created_at.strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    
    # AI Explanation
    writer.writerow(["AI Recommendation Summary"])
    writer.writerow([session.ai_explanation or "No explanation available"])
    writer.writerow([])
    
    # Vendor Results
    writer.writerow(["Vendor List"])
    writer.writerow(["Rank", "Vendor Name", "Final Score", "Reliability Score", "Risk Score", "Cost Score", "Reasoning"])
    
    # Sort vendors by rank
    sorted_vendors = sorted(session.vendor_results, key=lambda v: v.rank)
    for v in sorted_vendors:
        writer.writerow([
            v.rank,
            v.vendor_name,
            f"{v.final_score:.2f}",
            f"{v.reliability_score:.2f}",
            f"{v.risk_score:.2f}",
            f"{v.cost_score:.2f}",
            v.explanation or ""
        ])
    
    # 3. Stream back
    output.seek(0)
    # Sanitize filename
    safe_product_name = "".join([c if c.isalnum() else "_" for c in session.product_name])
    filename = f"procurement_results_{safe_product_name}_{session_id[:8]}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )