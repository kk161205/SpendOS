"""Reliability Analysis Node for vendor scoring (0-100)."""

import json
import logging
from app.graph.state import ProcurementWorkflowState, VendorData
from app.llm.groq_client import invoke_llm
from app.llm.model_router import WorkflowNode, get_model_for_node

logger = logging.getLogger(__name__)
MODEL_CFG = get_model_for_node(WorkflowNode.RELIABILITY_ANALYSIS)

SYSTEM_PROMPT = """You are a vendor reliability analyst. Evaluate the vendor's operational
reliability based on their profile. Return ONLY valid JSON:
{
  "reliability_score": <float 0-100, where 100=extremely reliable>,
  "reasoning": "<2-3 sentence explanation>",
  "breakdown": {
    "years_in_business_score": <float 0-100>,
    "certifications_score": <float 0-100>,
    "customer_satisfaction_score": <float 0-100>,
    "delivery_performance_score": <float 0-100>
  }
}"""


async def reliability_analysis_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Compute reliability scores and attach to existing ScoredVendor objects.
    """
    state.current_node = "reliability_analysis"

    for sv in state.scored_vendors:
        try:
            rel_score, reasoning, breakdown = await _analyze_reliability(
                sv.vendor_data, state.user_requirements
            )
            sv.reliability_score = rel_score
            sv.reliability_reasoning = reasoning
            sv.reliability_breakdown = breakdown
        except Exception as e:
            logger.warning(f"[reliability_analysis] Failed for {sv.vendor_data.name}: {e}")
            sv.reliability_score = _heuristic_reliability_score(sv.vendor_data)
            sv.reliability_reasoning = "Heuristic fallback due to LLM error."
            sv.reliability_breakdown = {}

    logger.info(f"[reliability_analysis] Completed for {len(state.scored_vendors)} vendors.")
    return state


async def _analyze_reliability(vendor: VendorData, req) -> tuple:
    """Call Groq LLM to reason about vendor reliability."""
    required_certs = getattr(req, "required_certifications", []) or []
    cert_overlap = [c for c in vendor.certifications if c in required_certs]

    user_prompt = (
        f"Vendor: {vendor.name}\n"
        f"Years in business: {vendor.years_in_business or 'Unknown'}\n"
        f"Certifications held: {', '.join(vendor.certifications) if vendor.certifications else 'None'}\n"
        f"Required certifications: {', '.join(required_certs) if required_certs else 'None'}\n"
        f"Certifications matched: {', '.join(cert_overlap) if cert_overlap else 'None'}\n"
        f"Average customer rating: {vendor.average_rating or 'N/A'}/5.0\n"
        f"Number of reviews: {vendor.review_count or 'N/A'}\n"
        f"On-time delivery rate: {vendor.on_time_delivery_rate or 'N/A'}%\n"
        f"Lead time: {vendor.lead_time_days or 'N/A'} days\n"
        f"Required delivery deadline: {req.delivery_deadline_days or 'N/A'} days\n\n"
        f"Provide reliability assessment as JSON."
    )

    response = await invoke_llm(
        model_name=MODEL_CFG.model_name,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=MODEL_CFG.temperature,
    )

    clean = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    data = json.loads(clean)

    rel_score = max(0.0, min(100.0, float(data.get("reliability_score", 50))))
    reasoning = data.get("reasoning", "")
    breakdown = data.get("breakdown", {})
    return rel_score, reasoning, breakdown


def _heuristic_reliability_score(vendor: VendorData) -> float:
    """Deterministic fallback when LLM unavailable."""
    score = 40.0

    if vendor.years_in_business:
        score += min(vendor.years_in_business * 2, 20)

    if vendor.certifications:
        score += min(len(vendor.certifications) * 5, 20)

    if vendor.average_rating:
        score += (vendor.average_rating / 5.0) * 20

    if vendor.on_time_delivery_rate:
        score += (vendor.on_time_delivery_rate / 100.0) * 20

    return max(0.0, min(100.0, score))
