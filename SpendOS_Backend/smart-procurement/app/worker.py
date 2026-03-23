"""
ARQ Worker — runs procurement background tasks in a separate process.

Start with:
    arq app.worker.WorkerSettings

Features over FastAPI BackgroundTasks:
  - Survives API server restarts (Redis-backed)
  - Automatic retries with exponential backoff
  - Horizontally scalable (run multiple workers)
"""

import logging
from arq.connections import RedisSettings

from app.config import get_settings
from app.database import init_db, async_session_factory
from app.graph.procurement_graph import run_procurement_workflow
from app.graph.state import UserRequirements
from app.models.task import ProcurementTask
from app.models.procurement import ProcurementSession, VendorResult
from app.schemas.procurement_schema import (
    ProcurementAnalysisResponse,
    VendorScoreResponse,
)

from sqlalchemy import select

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_procurement_task(ctx: dict, *, task_id: str, payload: dict, user_id: str):
    """
    ARQ task function. Runs the LangGraph procurement workflow and saves results.

    This is the equivalent of the old `run_procurement_background()` but now
    managed by ARQ with retry support and crash resilience.
    """
    logger.info(f"[arq_worker] Starting procurement workflow for task {task_id}")

    async with async_session_factory() as db:
        try:
            # Update status to processing
            result = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "processing"
                await db.commit()
                logger.info(f"[arq_worker] Task {task_id} marked as processing")
                
                # Notify SSE subscribers
                import json
                await ctx["redis"].publish(f"task_updates:{task_id}", json.dumps({"status": "processing"}))

            # Build requirements object from serialized payload
            requirements = UserRequirements(
                product_name=payload["product_name"],
                product_category=payload["product_category"],
                description=payload.get("description"),
                quantity=payload["quantity"],
                budget_usd=payload.get("budget_usd"),
                required_certifications=payload.get("required_certifications", []),
                delivery_deadline_days=payload.get("delivery_deadline_days"),
                cost_weight=payload.get("scoring_weights", {}).get("cost_weight", 0.35),
                reliability_weight=payload.get("scoring_weights", {}).get("reliability_weight", 0.40),
                risk_weight=payload.get("scoring_weights", {}).get("risk_weight", 0.25),
            )

            logger.info(f"[arq_worker] Triggering LangGraph workflow for '{payload['product_name']}'")
            final_state = await run_procurement_workflow(requirements)

            if final_state.error:
                logger.error(f"[arq_worker] Workflow returned error: {final_state.error}")
                raise Exception(final_state.error)

            logger.info(f"[arq_worker] Workflow completed. Ranked {len(final_state.ranked_vendors)} vendors.")

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
                product_name=payload["product_name"],
                product_category=payload["product_category"],
                status="completed",
                ranked_vendors=vendor_score_responses,
                ai_explanation=final_state.ai_explanation,
                total_vendors_evaluated=len(final_state.ranked_vendors),
                scoring_weights_used=payload.get("scoring_weights", {}),
            ).model_dump()

            # --- Caching Write-Back ---
            from app.utils.cache_utils import generate_procurement_hash_from_dict
            import json
            cache_key = generate_procurement_hash_from_dict(payload)
            
            # Push into Redis (7 Days TTL)
            await ctx["redis"].setex(cache_key, 7 * 24 * 3600, json.dumps(final_result))
            logger.info(f"[arq_worker] Wrote new results into cache `{cache_key}`")
            # --------------------------

            # Create session record
            procurement_session = ProcurementSession(
                user_id=user_id,
                product_name=payload["product_name"],
                category=payload["product_category"],
                budget=payload.get("budget_usd"),
                status="completed",
                ai_explanation=final_state.ai_explanation,
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
                    explanation=vendor_score.risk_reasoning,
                )
                db.add(vr)

            # Update the original task status to completed
            task_query = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task_to_update = task_query.scalar_one_or_none()
            if task_to_update:
                task_to_update.status = "completed"
                task_to_update.result = final_result
                
                # Notify SSE subscribers
                import json
                await ctx["redis"].publish(f"task_updates:{task_id}", json.dumps({
                    "status": "completed",
                    "result": final_result
                }))

            await db.commit()
            logger.info(f"[arq_worker] Successfully finished task {task_id}")

        except Exception as e:
            logger.error(f"[arq_worker] Task {task_id} failed: {e}", exc_info=True)
            result = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.result = {"error": str(e)}
                await db.commit()

                # Notify SSE subscribers
                import json
                await ctx["redis"].publish(f"task_updates:{task_id}", json.dumps({
                    "status": "failed",
                    "error": str(e)
                }))
            raise  # Re-raise so ARQ can track the failure and trigger retries


async def startup(ctx: dict):
    """ARQ worker startup hook — initialize the database."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("[arq_worker] Worker starting up — initializing DB...")
    await init_db()


async def shutdown(ctx: dict):
    """ARQ worker shutdown hook."""
    logger.info("[arq_worker] Worker shutting down.")


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [run_procurement_task]
    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    # Retry configuration
    max_tries = 3           # Retry up to 3 times on failure
    job_timeout = 120       # 2 minute timeout per job (AI pipeline can be slow)
    retry_defer_s = 10      # Base delay between retries (ARQ uses exponential backoff)

    # Health monitoring
    health_check_interval = 30  # seconds
