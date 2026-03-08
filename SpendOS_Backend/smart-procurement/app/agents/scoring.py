"""Scoring Node for weighted composite calculations."""

import logging
from app.graph.state import ProcurementWorkflowState

logger = logging.getLogger(__name__)


async def scoring_node(state: ProcurementWorkflowState) -> ProcurementWorkflowState:
    """
    Calculate the final weighted score for each vendor.
    Uses weights from user_requirements.
    """
    state.current_node = "scoring"
    req = state.user_requirements

    cw = req.cost_weight
    rw = req.reliability_weight
    riskw = req.risk_weight

    for sv in state.scored_vendors:
        sv.final_score = round(
            (cw * sv.cost_score)
            + (rw * sv.reliability_score)
            - (riskw * sv.risk_score),
            4,
        )

    logger.info(
        f"[scoring] Final scores computed for {len(state.scored_vendors)} vendors. "
        f"Weights — cost:{cw} reliability:{rw} risk:{riskw}"
    )
    return state
