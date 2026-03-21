import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    """
    Queue a background task to execute the full AI procurement pipeline.
    Returns immediately with a task_id.

    The task is enqueued to ARQ (Redis-backed) for reliable, retryable execution
    in a separate worker process.
    """
    logger.info(f"[/analyze] Received analysis request for '{payload.product_name}' by user '{current_user['user_id']}'")
    logger.debug(f"[/analyze] Payload: {payload.model_dump()}")

    request_id = str(uuid.uuid4())

    task = ProcurementTask(id=request_id, user_id=current_user["user_id"], status="pending")
    db.add(task)
    await db.commit()

    logger.info(f"[/analyze] Created ProcurementTask with ID: {request_id}. Enqueuing to ARQ.")
    arq_pool = request.app.state.arq_pool
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


@router.get("/history", response_model=list[ProcurementHistorySessionResponse])
async def get_procurement_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all past procurement sessions with their top vendors for the current user.
    """
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(ProcurementSession)
        .where(ProcurementSession.user_id == current_user["user_id"])
        .order_by(ProcurementSession.created_at.desc())
        .options(selectinload(ProcurementSession.vendor_results))
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

    return response