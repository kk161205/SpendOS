"""
ProcurementTask SQLAlchemy model — stores status and result of async background analysis.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base

class ProcurementTask(Base):
    __tablename__ = "procurement_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")
    result = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
