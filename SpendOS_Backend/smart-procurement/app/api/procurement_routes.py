import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_user
from app.database import get_db, async_session_factory
from app.models.task import ProcurementTask
from app.models.procurement import ProcurementSession, VendorResult
from app.graph.procurement_graph import run_procurement_workflow
from app.graph.state import UserRequirements
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
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a background task to execute the full AI procurement pipeline.
    Returns immediately with a task_id.
    """
    request_id = str(uuid.uuid4())
    
    task = ProcurementTask(id=request_id, user_id=current_user["user_id"], status="pending")
    db.add(task)
    await db.commit()
    
    background_tasks.add_task(run_procurement_background, request_id, payload, current_user["user_id"])
    
    return TaskAcceptedResponse(task_id=request_id, status="pending")


async def run_procurement_background(task_id: str, payload: ProcurementRequestSchema, user_id: str):
    """
    Background worker that runs the LangGraph workflow and saves the result to DB.
    """
    async with async_session_factory() as db:
        try:
            # Update status to processing
            result = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "processing"
                await db.commit()
            
            # Build requirements object
            requirements = UserRequirements(
                product_name=payload.product_name,
                product_category=payload.product_category,
                description=payload.description,
                quantity=payload.quantity,
                budget_usd=payload.budget_usd,
                required_certifications=payload.required_certifications or [],
                delivery_deadline_days=payload.delivery_deadline_days,
                cost_weight=payload.scoring_weights.cost_weight,
                reliability_weight=payload.scoring_weights.reliability_weight,
                risk_weight=payload.scoring_weights.risk_weight,
            )

            final_state = await run_procurement_workflow(requirements)

            if final_state.error:
                raise Exception(final_state.error)

            vendor_score_responses = []
            for sv in final_state.ranked_vendors:
                vendor_score_responses.append(VendorScoreResponse(
                    vendor_id=sv.vendor_data.vendor_id,
                    vendor_name=sv.vendor_data.name,
                    country=sv.vendor_data.country,
                    website=sv.vendor_data.website,
                    base_price_usd=sv.vendor_data.base_price_usd,
                    risk_score=sv.risk_score,
                    reliability_score=sv.reliability_score,
                    cost_score=sv.cost_score,
                    final_score=sv.final_score,
                    rank=sv.rank,
                    risk_reasoning=sv.risk_reasoning,
                    reliability_reasoning=sv.reliability_reasoning,
                    risk_breakdown=sv.risk_breakdown,
                    reliability_breakdown=sv.reliability_breakdown,
                    cost_breakdown=sv.cost_breakdown,
                ).model_dump())

            final_result = ProcurementAnalysisResponse(
                request_id=task_id,
                product_name=payload.product_name,
                status="completed",
                ranked_vendors=vendor_score_responses,
                ai_explanation=final_state.ai_explanation,
                total_vendors_evaluated=len(final_state.ranked_vendors),
                scoring_weights_used=payload.scoring_weights.model_dump(),
            ).model_dump()

            # Create Session
            procurement_session = ProcurementSession(
                user_id=user_id,
                product_name=payload.product_name,
                category=payload.product_category,
                budget=payload.budget_usd,
                status="completed",
                ai_explanation=final_state.ai_explanation
            )
            db.add(procurement_session)
            await db.flush() 
            
            for vendor_score in final_state.ranked_vendors:
                vr = VendorResult(
                    session_id=procurement_session.id,
                    vendor_id=vendor_score.vendor_data.vendor_id,
                    vendor_name=vendor_score.vendor_data.name,
                    final_score=vendor_score.final_score,
                    risk_score=vendor_score.risk_score,
                    reliability_score=vendor_score.reliability_score,
                    cost_score=vendor_score.cost_score,
                    rank=vendor_score.rank,
                    explanation=vendor_score.risk_reasoning
                )
                db.add(vr)

            # Update the original task status to completed
            task_query = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task_to_update = task_query.scalar_one_or_none()
            if task_to_update:
                task_to_update.status = "completed"
                task_to_update.result = final_result

            await db.commit()

        except Exception as e:
            logger.error(f"[background_task] Workflow failed for task {task_id}: {e}")
            result = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.result = {"error": str(e)}
                await db.commit()


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
            "ai_explanation": s.ai_explanation
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
