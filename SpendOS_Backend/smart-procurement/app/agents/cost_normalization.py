"""Node for deterministic price percentile normalization."""

import logging
from typing import List
from app.graph.state import ProcurementWorkflowState, ScoredVendor

logger = logging.getLogger(__name__)


async def cost_normalization_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """Compute cost scores using price percentile normalization."""
    state.current_node = "cost_normalization"
    req = state.user_requirements

    if not state.scored_vendors:
        logger.warning("[cost_normalization] No scored vendors to normalize.")
        return state

    # Compute effective unit price for each vendor
    effective_prices = []
    for sv in state.scored_vendors:
        price = _effective_price(sv, req.quantity)
        effective_prices.append(price)

    min_price = min(effective_prices) if effective_prices else 1.0
    max_price = max(effective_prices) if effective_prices else 1.0
    price_range = max_price - min_price if max_price != min_price else 1.0

    for sv, price in zip(state.scored_vendors, effective_prices):
        # Percentile: 0 = cheapest, 100 = most expensive
        percentile = ((price - min_price) / price_range) * 100 if price_range > 0 else 50

        # Cost score: higher is cheaper
        sv.cost_score = round(100 - percentile, 2)

        # Check budget constraint
        total_cost = price * req.quantity
        budget_ok = True
        if req.budget_usd and total_cost > req.budget_usd:
            budget_ok = False
            sv.cost_score = max(0.0, sv.cost_score - 20)  # Penalty for over budget

        sv.cost_breakdown = {
            "effective_unit_price_usd": round(price, 4),
            "estimated_total_cost_usd": round(total_cost, 2),
            "within_budget": budget_ok,
            "price_percentile": round(percentile, 2),
            "cost_score": sv.cost_score,
        }

    logger.info(f"[cost_normalization] Normalized costs for {len(state.scored_vendors)} vendors.")
    return state


def _effective_price(sv: ScoredVendor, quantity: int) -> float:
    """
    Determine the best available unit price for a vendor.
    Falls back through price_per_unit → base_price → 999999 sentinel.
    """
    v = sv.vendor_data
    if v.price_per_unit_usd and v.price_per_unit_usd > 0:
        return v.price_per_unit_usd
    if v.base_price_usd and v.base_price_usd > 0:
        return v.base_price_usd
    # No price data — assign a high sentinel to rank last on cost
    return 999_999.0
