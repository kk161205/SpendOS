"""
LangGraph shared workflow state.
Passed between all nodes in the procurement pipeline.
"""

from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class VendorData(BaseModel):
    """Vendor information collected and enriched during the workflow."""
    vendor_id: str
    name: str
    category: str
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    years_in_business: Optional[int] = None
    annual_revenue_usd: Optional[float] = None
    employee_count: Optional[int] = None
    is_publicly_traded: bool = False
    certifications: List[str] = Field(default_factory=list)
    base_price_usd: Optional[float] = None
    price_per_unit_usd: Optional[float] = None
    minimum_order_quantity: Optional[int] = None
    lead_time_days: Optional[int] = None
    average_rating: Optional[float] = None
    review_count: Optional[int] = None
    on_time_delivery_rate: Optional[float] = None
    # Enrichment extras
    payment_terms: Optional[str] = None
    incoterms: Optional[str] = None
    negative_news_mentions: int = 0
    compliance_issues: int = 0
    financial_stability_score: Optional[float] = None


class ScoredVendor(BaseModel):
    """Vendor with all computed scores."""
    vendor_data: VendorData
    risk_score: float = 50.0
    reliability_score: float = 50.0
    cost_score: float = 50.0
    final_score: float = 50.0
    rank: int = 0
    risk_reasoning: str = ""
    reliability_reasoning: str = ""
    risk_breakdown: dict = Field(default_factory=dict)
    reliability_breakdown: dict = Field(default_factory=dict)
    cost_breakdown: dict = Field(default_factory=dict)


class UserRequirements(BaseModel):
    """Structured user procurement requirements."""
    product_name: str
    product_category: str
    quantity: int
    budget_usd: float
    delivery_deadline_days: int
    payment_terms: str
    shipping_destination: str
    vendor_region_preference: Optional[str] = None
    incoterms: Optional[str] = None
    description: Optional[str] = None
    required_certifications: List[str] = Field(default_factory=list)
    cost_weight: float = 0.35
    reliability_weight: float = 0.40
    risk_weight: float = 0.25


class ProcurementWorkflowState(BaseModel):
    """
    Shared state passed through all LangGraph nodes.
    Each node reads from and writes to this state object.
    """
    # Input requirements (set once at workflow entry)
    user_requirements: Optional[UserRequirements] = None

    # Stage 1: Raw vendors from discovery
    vendors: List[VendorData] = Field(default_factory=list)

    # Stage 2: Enriched vendor data
    enriched_vendors: List[VendorData] = Field(default_factory=list)

    # Stage 3: Scored vendors (risk + reliability + cost)
    scored_vendors: List[ScoredVendor] = Field(default_factory=list)

    # Stage 4: Ranked vendors (sorted by final_score)
    ranked_vendors: List[ScoredVendor] = Field(default_factory=list)

    # Final output
    ai_explanation: str = ""

    # Tracking
    error: Optional[str] = None
    current_node: str = ""
