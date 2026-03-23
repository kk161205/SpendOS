"""Risk Analysis Node for vendor scoring (0-100)."""

import asyncio
import json
import logging
from app.graph.state import ProcurementWorkflowState, ScoredVendor, VendorData
from app.llm.groq_client import invoke_llm
from app.llm.model_router import WorkflowNode, get_model_for_node
from app.utils.sanitization import clean_llm_output

logger = logging.getLogger(__name__)
MODEL_CFG = get_model_for_node(WorkflowNode.RISK_ANALYSIS)

SYSTEM_PROMPT = """You are a procurement risk analyst. Given a vendor profile and user requirements,
provide a detailed risk assessment including commercial term mismatch. Return ONLY valid JSON:
{
  "risk_score": <float 0-100, where 0=no risk 100=extreme risk>,
  "reasoning": "<2-3 sentence explanation>",
  "breakdown": {
    "financial_risk": <float 0-100>,
    "news_sentiment_risk": <float 0-100>,
    "compliance_risk": <float 0-100>,
    "operational_maturity_risk": <float 0-100>,
    "commercial_term_risk": <float 0-100>,
    "logistics_risk": <float 0-100>
  }
}"""


async def risk_analysis_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Compute risk scores for all enriched vendors sequentially.
    Done sequentially deliberately to avoid LLM rate limits.
    Creates ScoredVendor objects with risk data.
    """
    state.current_node = "risk_analysis"
    
    # Define a wrapper to handle exceptions for each vendor
    async def _safe_analyze(vendor):
        try:
            risk_score, reasoning, breakdown = await _analyze_risk(vendor, state.user_requirements)
            return ScoredVendor(
                vendor_data=vendor,
                risk_score=risk_score,
                risk_reasoning=reasoning,
                risk_breakdown=breakdown,
            )
        except Exception as e:
            logger.warning(f"[risk_analysis] Failed for {vendor.name}, applying heuristic fallback: {e}")
            fallback_score = _heuristic_risk_score(vendor)
            return ScoredVendor(
                vendor_data=vendor,
                risk_score=fallback_score,
                risk_reasoning="Heuristic fallback due to LLM error.",
                risk_breakdown={},
            )

    scored_vendors = []
    for vendor in state.enriched_vendors:
        res = await _safe_analyze(vendor)
        scored_vendors.append(res)
    state.scored_vendors = scored_vendors
    
    logger.info(f"[risk_analysis] Scored risk for {len(state.scored_vendors)} vendors.")
    return state


async def _analyze_risk(vendor: VendorData, req):
    """Call Groq LLM to reason about vendor risk."""
    revenue_line = (
        f"Annual revenue: ${vendor.annual_revenue_usd:,.0f} USD"
        if vendor.annual_revenue_usd
        else "Annual revenue: Unknown"
    )

    user_prompt = (
        f"User Requirements:\n"
        f"- Target Budget: ${req.budget_usd or 'N/A'}\n"
        f"- Deadline: {req.delivery_deadline_days or 'N/A'} days\n"
        f"- Shipping Destination: {req.shipping_destination}\n"
        f"- Desired Payment Terms: {req.payment_terms}\n"
        f"- Desired Incoterms: {req.incoterms or 'Any'}\n\n"
        f"Vendor: {vendor.name}\n"
        f"Category: {vendor.category}\n"
        f"Country: {vendor.country or 'Unknown'}\n"
        f"Years in business: {vendor.years_in_business or 'Unknown'}\n"
        f"Financial stability score: {vendor.financial_stability_score or 50}/100\n"
        f"Negative news mentions: {vendor.negative_news_mentions}\n"
        f"Compliance issues: {vendor.compliance_issues}\n"
        f"Vendor Payment Terms: {vendor.payment_terms or 'Unknown'}\n"
        f"Vendor Incoterms: {vendor.incoterms or 'Unknown'}\n"
        f"Publicly traded: {vendor.is_publicly_traded}\n"
        f"{revenue_line}\n"
        f"\nProvide risk assessment as JSON, specifically considering if vendor's terms and location (relative to {req.shipping_destination}) create commercial or logistical risk."
    )

    response = await invoke_llm(
        model_name=MODEL_CFG.model_name,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=MODEL_CFG.temperature,
    )

    # Strip markdown fences if present
    clean = clean_llm_output(response)
    data = json.loads(clean)

    risk_score = max(0.0, min(100.0, float(data.get("risk_score", 50))))
    reasoning = data.get("reasoning", "")
    breakdown = data.get("breakdown", {})
    return risk_score, reasoning, breakdown


def _heuristic_risk_score(vendor: VendorData) -> float:
    """
    Deterministic fallback risk calculation when LLM is unavailable.
    """
    score = 50.0

    # Financial stability (inverted: high stability = low risk)
    if vendor.financial_stability_score is not None:
        score -= (vendor.financial_stability_score - 50) * 0.3

    # Negative news
    score += vendor.negative_news_mentions * 5

    # Compliance issues
    score += vendor.compliance_issues * 8

    # Operational maturity
    if vendor.years_in_business:
        if vendor.years_in_business >= 10:
            score -= 10
        elif vendor.years_in_business < 3:
            score += 15

    return max(0.0, min(100.0, score))
