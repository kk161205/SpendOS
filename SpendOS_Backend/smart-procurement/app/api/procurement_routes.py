import io
import csv
import logging
import uuid
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user
from app.models.task import ProcurementTask
from app.models.procurement import ProcurementSession
from app.services.procurement_service import ProcurementService
from app.schemas.procurement_schema import (
    TaskAcceptedResponse,
    TaskStatusResponse,
    ProcurementHistorySessionResponse,
    ProcurementHistoryPaginatedResponse,
    ProcurementRequest as ProcurementRequestSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/procurement", tags=["Procurement"])

@router.post("/analyze", response_model=TaskAcceptedResponse)
async def analyze_procurement(
    payload: ProcurementRequestSchema,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue or return cached procurement analysis."""
    result = await ProcurementService.analyze(
        payload, 
        current_user["user_id"], 
        request.app.state.arq_pool, 
        db
    )
    return TaskAcceptedResponse(**result)


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of a background task."""
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


@router.get("/events/{task_id}")
async def task_events(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) endpoint for real-time task updates.
    """
    async def event_generator():
        # 1. Check current status in DB first (could already be finished)
        stmt = select(ProcurementTask).where(
            ProcurementTask.id == task_id,
            ProcurementTask.user_id == current_user["user_id"]
        )
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        
        if not task:
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
            return

        if task.status in ["completed", "failed"]:
            yield f"data: {json.dumps({'status': task.status, 'result': task.result})}\n\n"
            return

        # 2. Subscribe to Redis for future updates
        pool = request.app.state.arq_pool
        async with pool.pubsub() as pubsub:
            await pubsub.subscribe(f"task_updates:{task_id}")
            logger.info(f"[sse] Subscribed to task_updates:{task_id}")

            try:
                while True:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.info(f"[sse] Client disconnected from {task_id}")
                        break

                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        data = message["data"].decode("utf-8")
                        yield f"data: {data}\n\n"
                        
                        # Stop if we reach a terminal state
                        parsed = json.loads(data)
                        if parsed.get("status") in ["completed", "failed"]:
                            break
                    
                    await asyncio.sleep(0.1)
            finally:
                await pubsub.unsubscribe(f"task_updates:{task_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for Nginx/Cloudflare
        }
    )


@router.get("/history", response_model=ProcurementHistoryPaginatedResponse)
async def get_procurement_history(
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated history."""
    total, sessions = await ProcurementService.get_history(current_user["user_id"], limit, offset, db)
    
    response = []
    for s in sessions:
        vendor_dicts = []
        for v in s.vendor_results:
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
            "budget_usd": s.budget,
            "payment_terms": s.payment_terms,
            "shipping_destination": s.shipping_destination,
            "incoterms": s.incoterms,
            "delivery_deadline_days": s.delivery_deadline_days,
            "vendor_region_preference": s.vendor_region_preference,
        }
        
        response.append(ProcurementHistorySessionResponse(
            id=s.id,
            timestamp=s.created_at.isoformat(),
            product_name=s.product_name,
            category=s.category,
            status=s.status,
            results=results_obj,
        ))

    return ProcurementHistoryPaginatedResponse(total=total, items=response)


@router.delete("/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procurement_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session."""
    success = await ProcurementService.delete_session(session_id, current_user["user_id"], db)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or forbidden")
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
    
    # 2. Generate CSV using utility
    from app.utils.export import ProcurementExporter
    output = ProcurementExporter.generate_csv(session)
    
    # 3. Stream back
    # Sanitize filename
    safe_product_name = "".join([c if c.isalnum() else "_" for c in session.product_name])
    filename = f"procurement_results_{safe_product_name}_{session_id[:8]}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )