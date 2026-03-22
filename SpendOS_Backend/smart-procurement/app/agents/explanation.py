"""Explanation Node for AI recommendation report generation."""

import logging
from app.graph.state import ProcurementWorkflowState
from app.llm.groq_client import invoke_llm
from app.llm.model_router import WorkflowNode, get_model_for_node
from app.utils.sanitization import clean_llm_output

logger = logging.getLogger(__name__)
MODEL_CFG = get_model_for_node(WorkflowNode.EXPLANATION)

SYSTEM_PROMPT = """You are a procurement advisor. Write a concise, professional 
procurement recommendation report (3-4 paragraphs) based on the analysis results. 
Explain why the top vendor was selected, highlight key risks and reliability factors, 
and mention cost considerations. Write clearly for a business audience."""


async def explanation_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Generate a natural language explanation for the procurement recommendation.
    """
    state.current_node = "explanation"

    if not state.ranked_vendors:
        state.ai_explanation = "No vendors were found matching your requirements."
        return state

    try:
        explanation = await _generate_explanation(state)
        state.ai_explanation = explanation
        logger.info("[explanation] Successfully generated AI recommendation.")
    except Exception as e:
        logger.warning(f"[explanation] LLM failed to generate explanation, using fallback: {e}", exc_info=True)
        state.ai_explanation = _fallback_explanation(state)

    logger.info("[explanation] Generated AI recommendation.")
    return state


async def _generate_explanation(state: ProcurementWorkflowState) -> str:
    """Call Groq LLM to generate the explanation."""
    req = state.user_requirements
    top_vendors = state.ranked_vendors[:3]

    vendor_summaries = []
    for sv in top_vendors:
        vendor_summaries.append(
            f"Rank #{sv.rank}: {sv.vendor_data.name}\n"
            f"  - Final Score: {sv.final_score:.2f}\n"
            f"  - Risk Score: {sv.risk_score:.1f} (lower=better)\n"
            f"  - Reliability Score: {sv.reliability_score:.1f} (higher=better)\n"
            f"  - Cost Score: {sv.cost_score:.1f} (higher=cheaper)\n"
            f"  - Risk Reasoning: {sv.risk_reasoning}\n"
            f"  - Reliability Reasoning: {sv.reliability_reasoning}\n"
        )

    user_prompt = (
        f"Procurement Request:\n"
        f"- Product: {req.product_name}\n"
        f"- Category: {req.product_category}\n"
        f"- Quantity: {req.quantity}\n"
        f"- Budget: ${req.budget_usd or 'unlimited'}\n"
        f"- Scoring weights: cost={req.cost_weight}, "
        f"reliability={req.reliability_weight}, risk={req.risk_weight}\n\n"
        f"Top Vendor Analysis:\n" + "\n".join(vendor_summaries) + "\n\n"
        f"Total vendors evaluated: {len(state.ranked_vendors)}\n\n"
        f"Write a professional procurement recommendation."
    )

    response = await invoke_llm(
        model_name=MODEL_CFG.model_name,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=MODEL_CFG.temperature,
    )
    return clean_llm_output(response)


def _fallback_explanation(state: ProcurementWorkflowState) -> str:
    """Deterministic fallback explanation when LLM unavailable."""
    if not state.ranked_vendors:
        return "No vendors found."
    top = state.ranked_vendors[0]
    return (
        f"Based on analysis of {len(state.ranked_vendors)} vendors, "
        f"{top.vendor_data.name} is the recommended vendor with a composite "
        f"score of {top.final_score:.2f}. "
        f"Risk score: {top.risk_score:.1f}/100 (lower is better). "
        f"Reliability score: {top.reliability_score:.1f}/100. "
        f"Cost score: {top.cost_score:.1f}/100."
    )
