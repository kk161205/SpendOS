"""
ARQ Worker — runs procurement background tasks in a separate process.

Start with:
    arq app.worker.WorkerSettings

Features over FastAPI BackgroundTasks:
  - Survives API server restarts (Redis-backed)
  - Automatic retries with exponential backoff
  - Horizontally scalable (run multiple workers)
"""

import json
import logging

from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_factory
from app.graph.procurement_graph import run_procurement_workflow
from app.graph.state import UserRequirements
from app.models.procurement import ProcurementSession, VendorResult
from app.models.task import ProcurementTask
from app.schemas.procurement_schema import ProcurementAnalysisResponse, VendorScoreResponse
from app.utils.cache_utils import generate_procurement_hash_from_dict
from app.graph.state import UserRequirements

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_procurement_task(ctx: dict, *, task_id: str, payload: dict, user_id: str):
    """
    ARQ task function. Runs the LangGraph procurement workflow and saves results.
    """
    # Contextual logging for better traceability
    log_prefix = f"[Task:{task_id}]"
    logger.info(f"{log_prefix} Starting procurement workflow")

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
                await ctx["redis"].publish(f"task_updates:{task_id}", json.dumps({"status": "processing"}))

            # Build requirements object from serialized payload
            requirements = UserRequirements(
                product_name=payload["product_name"],
                product_category=payload["product_category"],
                description=payload.get("description"),
                quantity=payload["quantity"],
                budget_usd=payload["budget_usd"],
                payment_terms=payload["payment_terms"],
                shipping_destination=payload["shipping_destination"],
                vendor_region_preference=payload.get("vendor_region_preference"),
                incoterms=payload.get("incoterms"),
                required_certifications=payload.get("required_certifications", []),
                delivery_deadline_days=payload["delivery_deadline_days"],
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

            # Skipping explicit Redis cache write (Migrating to Postgres Caching later)

            # 4. Save to historical session for the user
            proc_session = ProcurementSession(
                user_id=user_id,
                product_name=requirements.product_name,
                category=requirements.product_category,
                budget=requirements.budget_usd,
                shipping_destination=requirements.shipping_destination,
                vendor_region_preference=requirements.vendor_region_preference,
                payment_terms=requirements.payment_terms,
                incoterms=requirements.incoterms,
                delivery_deadline_days=requirements.delivery_deadline_days,
                ai_explanation=final_state.ai_explanation,
                status="completed"
            )
            db.add(proc_session)
            await db.flush()

            for vendor_score in final_state.ranked_vendors:
                vr = VendorResult(
                    session_id=proc_session.id,
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
                await ctx["redis"].publish(f"task_updates:{task_id}", json.dumps({
                    "status": "completed",
                    "result": final_result
                }))

            await db.commit()
            logger.info(f"[arq_worker] Successfully finished task {task_id}")

        except Exception as e:
            logger.error(f"[arq_worker] Task {task_id} failed: {e}", exc_info=True)
            await db.rollback()  # Recover from broken transaction state
            
            result = await db.execute(select(ProcurementTask).where(ProcurementTask.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.result = {"error": str(e)}
                await db.commit()

                # Notify SSE subscribers
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
    logger.info("[arq_worker] Worker starting up...")


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

    # Redis Garbage Collection
    keep_result = 3600      # 1 hour TTL
    keep_result_forever = False

    # Health monitoring
    health_check_interval = 30  # seconds
