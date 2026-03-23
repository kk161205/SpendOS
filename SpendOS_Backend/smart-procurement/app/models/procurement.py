"""
Procurement Models — store historical procurement session results.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ProcurementSession(Base):
    __tablename__ = "procurement_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="General")
    budget = Column(Float, nullable=True)
    shipping_destination = Column(String, nullable=True)
    vendor_region_preference = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    incoterms = Column(String, nullable=True)
    delivery_deadline_days = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="completed")
    ai_explanation = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship back to VendorResult
    vendor_results = relationship("VendorResult", back_populates="session", cascade="all, delete-orphan")


class VendorResult(Base):
    __tablename__ = "vendor_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("procurement_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(String, nullable=True)  # ID from discovery agent
    vendor_name = Column(String, nullable=False)
    final_score = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    reliability_score = Column(Float, nullable=False)
    cost_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    explanation = Column(String, nullable=True)

    session = relationship("ProcurementSession", back_populates="vendor_results")
