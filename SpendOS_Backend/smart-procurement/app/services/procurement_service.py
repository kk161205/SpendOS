import logging
import uuid
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.task import ProcurementTask
from app.models.procurement import ProcurementSession
from app.utils.cache_utils import generate_procurement_hash

logger = logging.getLogger(__name__)

class ProcurementService:
    @staticmethod
    async def analyze(payload, user_id: str, arq_pool, db: AsyncSession):
        """Logic for queueing or returning cached procurement analysis."""
        request_id = str(uuid.uuid4())
        cache_key = generate_procurement_hash(payload)

        # 1. Check Cache
        stmt = (
            select(ProcurementTask)
            .where(
                ProcurementTask.status == "completed",
                ProcurementTask.cache_key == cache_key,
            )
            .order_by(ProcurementTask.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        cached_task = result.scalar_one_or_none()

        if cached_task and cached_task.result:
            logger.info(f"[service] Cache hit for '{payload.product_name}'")
            cached_result = dict(cached_task.result)
            cached_result["request_id"] = request_id
            
            task = ProcurementTask(id=request_id, user_id=user_id, status="completed", result=cached_result)
            db.add(task)
            await db.commit()
            return {"task_id": request_id, "status": "pending"}

        # 2. Cache Miss -> Queue
        task = ProcurementTask(id=request_id, user_id=user_id, status="pending", cache_key=cache_key)
        db.add(task)
        await db.commit()

        await arq_pool.enqueue_job(
            "run_procurement_task",
            task_id=request_id,
            payload=payload.model_dump(),
            user_id=user_id,
        )
        return {"task_id": request_id, "status": "pending"}

    @staticmethod
    async def get_history(user_id: str, limit: int, offset: int, db: AsyncSession) -> Tuple[int, List[ProcurementSession]]:
        """Paginated history logic."""
        count_stmt = select(func.count(ProcurementSession.id)).where(ProcurementSession.user_id == user_id)
        total_count = await db.scalar(count_stmt)

        stmt = (
            select(ProcurementSession)
            .where(ProcurementSession.user_id == user_id)
            .order_by(ProcurementSession.created_at.desc())
            .options(selectinload(ProcurementSession.vendor_results))
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        return total_count, sessions

    @staticmethod
    async def delete_session(session_id: str, user_id: str, db: AsyncSession):
        """Deletion logic."""
        stmt = select(ProcurementSession).where(
            ProcurementSession.id == session_id,
            ProcurementSession.user_id == user_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            return False
        
        await db.delete(session)
        await db.commit()
        return True
