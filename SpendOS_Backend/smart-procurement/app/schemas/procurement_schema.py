"""Pydantic schemas for procurement API."""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from app.utils.sanitization import sanitize_for_llm


class ScoringWeights(BaseModel):
    """Configurable weights for the final vendor score formula."""
    cost_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    reliability_weight: float = Field(default=0.40, ge=0.0, le=1.0)
    risk_weight: float = Field(default=0.25, ge=0.0, le=1.0)

    @field_validator("risk_weight")
    @classmethod
    def weights_must_sum_to_one(cls, v, info):
        values = info.data
        total = values.get("cost_weight", 0.35) + values.get("reliability_weight", 0.40) + v
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.2f}"
            )
        return v


class ProcurementRequest(BaseModel):
    """Input payload for procurement analysis."""
    product_name: str = Field(..., min_length=2, max_length=255,
                               description="Name of the product to procure")
    product_category: str = Field(..., min_length=2, max_length=100,
                                   description="Category (e.g., electronics, chemicals)")
    description: Optional[str] = Field(None, max_length=2000,
                                        description="Detailed requirements")
    quantity: int = Field(..., gt=0, description="Required quantity")
    budget_usd: Optional[float] = Field(None, gt=0, description="Maximum budget in USD")
    required_certifications: Optional[List[str]] = Field(
        default=None, description="e.g., ['ISO 9001', 'CE Mark']"
    )
    delivery_deadline_days: Optional[int] = Field(
        None, gt=0, description="Delivery required within N days"
    )
    scoring_weights: ScoringWeights = Field(
        default_factory=ScoringWeights,
        description="Configurable scoring weights"
    )

    @field_validator("product_name", "description", mode="before")
    @classmethod
    def sanitize_llm_inputs(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_for_llm(v)


class VendorScoreResponse(BaseModel):
    """Scored vendor returned in analysis results."""
    vendor_id: str
    vendor_name: str
    country: Optional[str]
    website: Optional[str] = None
    base_price_usd: Optional[float]
    risk_score: float = Field(description="0=low risk, 100=high risk")
    reliability_score: float = Field(description="0=unreliable, 100=very reliable")
    cost_score: float = Field(description="0=expensive, 100=cheapest")
    final_score: float = Field(description="Weighted composite score")
    rank: int
    risk_reasoning: Optional[str]
    reliability_reasoning: Optional[str]
    risk_breakdown: Optional[dict]
    reliability_breakdown: Optional[dict]
    cost_breakdown: Optional[dict]

    class Config:
        from_attributes = True


class ProcurementAnalysisResponse(BaseModel):
    """Full response from the procurement analysis endpoint."""
    request_id: str
    product_name: str
    product_category: str
    status: str
    ranked_vendors: List[VendorScoreResponse]
    ai_explanation: str
    total_vendors_evaluated: int
    scoring_weights_used: ScoringWeights


class TaskAcceptedResponse(BaseModel):
    """Immediate response after submitting a procurement analysis task."""
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response when polling for task status."""
    task_id: str
    status: str
    result: Optional[ProcurementAnalysisResponse] = None


class ProcurementHistorySessionResponse(BaseModel):
    id: str
    timestamp: str
    product_name: str
    category: str = "General"
    status: str
    results: Optional[dict] = None  # Using dict since we construct it manually

class ProcurementHistoryPaginatedResponse(BaseModel):
    total: int
    items: List[ProcurementHistorySessionResponse]