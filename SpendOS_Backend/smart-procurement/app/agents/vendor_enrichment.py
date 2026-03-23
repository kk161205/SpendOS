"""Vendor Enrichment Node for risk signal estimation."""

import asyncio
import json
import logging
from app.graph.state import ProcurementWorkflowState, VendorData
from app.llm.groq_client import invoke_llm
from app.llm.model_router import WorkflowNode, get_model_for_node
from app.utils.sanitization import clean_llm_output
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)
MODEL_CFG = get_model_for_node(WorkflowNode.VENDOR_ENRICHMENT)

SYSTEM_PROMPT = """You are a vendor intelligence analyst. Analyze the vendor profile and 
estimate risk signals. Return ONLY valid JSON with these exact keys:
{
  "financial_stability_score": <float 0-100>,
  "negative_news_mentions": <int 0-10>,
  "compliance_issues": <int 0-5>,
  "enrichment_notes": "<string>"
}
Do not include any explanation or markdown."""


async def vendor_enrichment_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Enrich vendor profiles using LLM analysis in parallel.
    Populates state.enriched_vendors from state.vendors.
    """
    state.current_node = "vendor_enrichment"

    # Process vendors sequentially to avoid rate limits
    results = []
    for vendor in state.vendors:
        try:
            res = await _enrich_vendor(vendor)
            results.append(res)
        except Exception as e:
            results.append(e)

    enriched = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            vendor = state.vendors[i]
            logger.warning(f"[vendor_enrichment] Failed to enrich {vendor.name}, using fallback: {res}")
            enriched.append(vendor)
        else:
            enriched.append(res)
            logger.info(f"[vendor_enrichment] Successfully enriched {res.name}")

    state.enriched_vendors = enriched
    logger.info(f"[vendor_enrichment] Enriched {len(enriched)}/{len(state.vendors)} vendors.")
    return state


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
async def _enrich_vendor(vendor: VendorData) -> VendorData:
    """Call Groq LLM to enrich a single vendor with risk signals."""
    revenue_line = (
        f"- Annual revenue: ${vendor.annual_revenue_usd:,.0f} USD"
        if vendor.annual_revenue_usd
        else "- Annual revenue: Unknown"
    )

    user_prompt = (
        f"Vendor Profile:\n"
        f"- Name: {vendor.name}\n"
        f"- Category: {vendor.category}\n"
        f"- Country: {vendor.country or 'Unknown'}\n"
        f"- Years in business: {vendor.years_in_business or 'Unknown'}\n"
        f"{revenue_line}\n"
        f"- Publicly traded: {vendor.is_publicly_traded}\n"
        f"- Employee count: {vendor.employee_count or 'Unknown'}\n"
        f"- Certifications: {', '.join(vendor.certifications) if vendor.certifications else 'None'}\n"
        f"- Average rating: {vendor.average_rating or 'N/A'}\n"
        f"- On-time delivery rate: {vendor.on_time_delivery_rate or 'N/A'}%\n"
        f"- Description: {vendor.description or 'N/A'}\n\n"
        f"Estimate the vendor's risk signals as JSON."
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

    vendor.financial_stability_score = float(data.get("financial_stability_score", 50))
    vendor.negative_news_mentions = int(data.get("negative_news_mentions", 0))
    vendor.compliance_issues = int(data.get("compliance_issues", 0))

    return vendor
