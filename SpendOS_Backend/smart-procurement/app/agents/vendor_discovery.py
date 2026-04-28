"""Vendor Discovery Node using SerpAPI."""

import asyncio
import json
import logging
from typing import List
from serpapi import GoogleSearch
from tenacity import retry, stop_after_attempt, wait_exponential

from app.graph.state import ProcurementWorkflowState, VendorData
from app.llm.groq_client import invoke_llm
from app.llm.model_router import WorkflowNode, get_model_for_node
from app.utils.sanitization import clean_llm_output
from app.config import get_settings
from app.exceptions import VendorDiscoveryError

logger = logging.getLogger(__name__)
settings = get_settings()
MODEL_CFG = get_model_for_node(WorkflowNode.VENDOR_DISCOVERY)

from app.agents.prompts import VENDOR_DISCOVERY_SYSTEM as SYSTEM_PROMPT


async def vendor_discovery_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Discover vendors by searching the web via SerpAPI,
    then parse results into structured VendorData using LLM.
    """
    state.current_node = "vendor_discovery"
    req = state.user_requirements
    logger.info(f"[vendor_discovery] Searching online for: {req.product_name} in {req.product_category}")

    try:
        search_results = await _search_vendors_online(req)

        if not search_results:
            logger.warning(f"[vendor_discovery] No search results found for query parameters: {req.product_name} / {req.product_category}")
            state.vendors = []
            return state

        vendors = await _extract_vendors_from_results(search_results, req)

        state.vendors = vendors
        logger.info(f"[vendor_discovery] Discovered {len(vendors)} vendors.")
        return state

    except Exception as e:
        logger.error(f"[vendor_discovery] Final error after retries: {e}")
        raise VendorDiscoveryError(f"Vendor discovery process failed completely: {str(e)}") from e


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
async def _search_vendors_online(req) -> List[dict]:
    """
    Use SerpAPI to search Google for vendor/supplier information.
    Queries run in parallel via asyncio.gather for ~2× speedup.
    Returns a deduplicated list of organic search result dicts.
    """
    queries = [
        f"{req.product_name} B2B wholesale suppliers shipping to {req.shipping_destination}",
        f"top {req.product_category} manufacturers {req.product_name} serving {req.shipping_destination}",
    ]

    # Fire all queries in parallel for speed
    tasks = [_run_single_query(q) for q in queries]
    query_results = await asyncio.gather(*tasks)

    # Merge results, skipping any that raised exceptions
    all_results = []
    for i, result in enumerate(query_results):
        if isinstance(result, Exception):
            logger.error(f"[vendor_discovery] Query '{queries[i]}' failed: {result}")
        else:
            all_results.extend(result)

    # Deduplicate by link
    seen_links: set[str] = set()
    unique_results = []
    for r in all_results:
        link = r.get("link", "")
        if link not in seen_links:
            seen_links.add(link)
            unique_results.append(r)

    return unique_results[:15]  # Cap at 15 results


async def _run_single_query(query: str, timeout_seconds: float = 15.0) -> List[dict]:
    """
    Execute a single SerpAPI query with timeout and automatic
    geo-lock fallback if no results are returned.
    """
    try:
        return await asyncio.wait_for(
            _execute_serp_query(query), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.error(f"[vendor_discovery] SerpAPI query timed out after {timeout_seconds}s: '{query}'")
        return []


async def _execute_serp_query(query: str) -> List[dict]:
    """Run SerpAPI search, falling back to a broader query if needed."""
    search = GoogleSearch({
        "q": query,
        "api_key": settings.serp_api_key,
        "num": 10,
        "engine": "google",
        "gl": "us",
        "hl": "en",
    })
    results = await asyncio.to_thread(search.get_dict)

    # SerpAPI returns errors in the dictionary payload
    if "error" in results:
        logger.error(f"[vendor_discovery] SerpAPI returned an error: {results['error']}")
        return []

    organic = results.get("organic_results", [])

    # Fallback: retry without geo-locks if 0 results
    if not organic:
        logger.info(f"[vendor_discovery] Query '{query}' yielded 0 results, retrying without location bounds...")
        broad_search = GoogleSearch({
            "q": query,
            "api_key": settings.serp_api_key,
            "num": 10,
            "engine": "google",
        })
        broad_results = await asyncio.to_thread(broad_search.get_dict)
        if "error" in broad_results:
            logger.error(f"[vendor_discovery] SerpAPI returned an error on retry: {broad_results['error']}")
            return []
        organic = broad_results.get("organic_results", [])

    logger.info(f"[vendor_discovery] SerpAPI query '{query}' → {len(organic)} results")
    return organic


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
async def _extract_vendors_from_results(
    search_results: List[dict], req
) -> List[VendorData]:
    """Use Groq LLM to extract structured vendor data from search results."""
    # Format search results for the LLM
    formatted_results = []
    for i, r in enumerate(search_results, 1):
        formatted_results.append(
            f"{i}. Title: {r.get('title', 'N/A')}\n"
            f"   Link: {r.get('link', 'N/A')}\n"
            f"   Snippet: {r.get('snippet', 'N/A')}\n"
        )

    user_prompt = (
        f"User is looking for vendors/suppliers for:\n"
        f"- Product: {req.product_name}\n"
        f"- Category: {req.product_category}\n"
        f"- Quantity needed: {req.quantity}\n"
        f"- Target Budget: ${req.budget_usd or 'not specified'}\n"
        f"- Shipping Destination: {req.shipping_destination}\n"
        f"- Preferred Region: {req.vendor_region_preference or 'No preference'}\n"
        f"- Required certifications: {req.required_certifications or 'none'}\n\n"
        f"Here are Google search results about potential suppliers:\n\n"
        f"{''.join(formatted_results)}\n\n"
        f"Extract vendor information from these results. "
        f"For each distinct vendor/supplier found, provide structured data. "
        f"Estimate pricing, ratings, and other metrics based on available info "
        f"and industry standards. Return as a JSON array."
    )

    try:
        response = await invoke_llm(
            model_name=MODEL_CFG.model_name,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=MODEL_CFG.temperature,
        )

        logger.debug(f"[vendor_discovery] Raw LLM response (first 500 chars): {response[:500]}")

        # Strip markdown fences if present (e.g. ```json ... ```)
        clean = clean_llm_output(response)

        try:
            vendor_dicts = json.loads(clean)
        except Exception as e:
            logger.error(f"[vendor_discovery] JSON parse error: {e}")
            logger.debug(f"[vendor_discovery] Raw response: {response}")
            return []

        if not isinstance(vendor_dicts, list):
            logger.warning("[vendor_discovery] LLM returned non-list, wrapping.")
            vendor_dicts = [vendor_dicts]

        vendors = []
        for i, vd in enumerate(vendor_dicts):
            try:
                vendor = _dict_to_vendor_data(vd, i)
                vendors.append(vendor)
            except Exception as e:
                logger.warning(f"[vendor_discovery] Failed to parse vendor {i}: {e}")

        # Cap at 5 vendors to balance comprehensive analysis and token usage
        return vendors[:5]

    except json.JSONDecodeError as e:
        logger.error(f"[vendor_discovery] JSON parse error: {e}. Raw response: {response[:500] if 'response' in dir() else 'N/A'}")
        return []
    except Exception as e:
        logger.error(f"[vendor_discovery] LLM extraction failed: {e}", exc_info=True)
        return []


def _dict_to_vendor_data(d: dict, index: int) -> VendorData:
    """Convert a dict (from LLM JSON) to a VendorData dataclass."""
    import uuid

    certs = d.get("certifications", [])
    if isinstance(certs, str):
        certs = [certs]

    return VendorData(
        vendor_id=str(uuid.uuid4()),
        name=d.get("name", f"Vendor {index + 1}"),
        category=d.get("category", "unknown"),
        country=d.get("country"),
        website=d.get("website"),
        description=d.get("description"),
        years_in_business=_safe_int(d.get("years_in_business")),
        annual_revenue_usd=_safe_float(d.get("annual_revenue_usd")),
        employee_count=_safe_int(d.get("employee_count")),
        is_publicly_traded=bool(d.get("is_publicly_traded", False)),
        certifications=certs,
        base_price_usd=_safe_float(d.get("base_price_usd")),
        price_per_unit_usd=_safe_float(d.get("price_per_unit_usd")),
        minimum_order_quantity=_safe_int(d.get("minimum_order_quantity")),
        lead_time_days=_safe_int(d.get("lead_time_days")),
        average_rating=_safe_float(d.get("average_rating")),
        review_count=_safe_int(d.get("review_count")),
        on_time_delivery_rate=_safe_float(d.get("on_time_delivery_rate")),
    )


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
