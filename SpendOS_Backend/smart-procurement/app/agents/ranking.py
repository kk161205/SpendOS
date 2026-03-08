"""Ranking Node for sorting vendors by final score."""

import logging
from app.graph.state import ProcurementWorkflowState

logger = logging.getLogger(__name__)


async def ranking_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Sort scored_vendors by final_score descending and assign rank.
    Populate state.ranked_vendors.
    """
    state.current_node = "ranking"

    sorted_vendors = sorted(
        state.scored_vendors,
        key=lambda sv: sv.final_score,
        reverse=True,
    )

    for rank, sv in enumerate(sorted_vendors, start=1):
        sv.rank = rank

    state.ranked_vendors = sorted_vendors

    if sorted_vendors:
        top = sorted_vendors[0]
        logger.info(
            f"[ranking] Ranked {len(sorted_vendors)} vendors. "
            f"Top vendor: {top.vendor_data.name} (score={top.final_score:.2f})"
        )
    return state
