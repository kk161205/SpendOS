"""
Procurement LangGraph Workflow.
Assembles all agent nodes into a deterministic sequential pipeline.

Pipeline:
  vendor_discovery → vendor_enrichment → risk_analysis → reliability_analysis
  → cost_normalization → scoring → ranking → explanation
"""

import logging
from langgraph.graph import StateGraph, END
from app.graph.state import ProcurementWorkflowState, UserRequirements
from app.agents.vendor_discovery import vendor_discovery_node
from app.agents.vendor_enrichment import vendor_enrichment_node
from app.agents.risk_analysis import risk_analysis_node
from app.agents.reliability_analysis import reliability_analysis_node
from app.agents.cost_normalization import cost_normalization_node
from app.agents.scoring import scoring_node
from app.agents.ranking import ranking_node
from app.agents.explanation import explanation_node
from app.exceptions import VendorDiscoveryError

logger = logging.getLogger(__name__)


def _should_continue(state: ProcurementWorkflowState) -> str:
    """Route to END if an error occurred, otherwise continue."""
    if state.error:
        logger.error(f"[graph] Workflow halted at {state.current_node}: {state.error}")
        return "end"
    return "continue"


def build_procurement_graph() -> StateGraph:
    """
    Build and compile the LangGraph procurement workflow.
    
    Returns:
        Compiled LangGraph StateGraph ready for .ainvoke()
    """
    # LangGraph requires the state type to be a dict or TypedDict for built-in support.
    # We wrap our dataclass in adapter functions.
    
    graph = StateGraph(dict)

    # Register all nodes
    graph.add_node("vendor_discovery", _wrap(vendor_discovery_node))
    graph.add_node("vendor_enrichment", _wrap(vendor_enrichment_node))
    graph.add_node("risk_analysis", _wrap(risk_analysis_node))
    graph.add_node("reliability_analysis", _wrap(reliability_analysis_node))
    graph.add_node("cost_normalization", _wrap(cost_normalization_node))
    graph.add_node("scoring", _wrap(scoring_node))
    graph.add_node("ranking", _wrap(ranking_node))
    graph.add_node("explanation", _wrap(explanation_node))

    # Set entry point
    graph.set_entry_point("vendor_discovery")

    # Sequential edges
    graph.add_edge("vendor_discovery", "vendor_enrichment")
    graph.add_edge("vendor_enrichment", "risk_analysis")
    graph.add_edge("risk_analysis", "reliability_analysis")
    graph.add_edge("reliability_analysis", "cost_normalization")
    graph.add_edge("cost_normalization", "scoring")
    graph.add_edge("scoring", "ranking")
    graph.add_edge("ranking", "explanation")
    graph.add_edge("explanation", END)

    return graph.compile()


def _wrap(node_fn):
    """
    Adapter: converts dict state ↔ ProcurementWorkflowState dataclass.
    LangGraph passes/returns dicts; our agents use the typed dataclass.
    """
    async def wrapped(state_dict: dict) -> dict:
        state = state_dict.get("_state")
        if state is None:
            state = ProcurementWorkflowState()
        result = await node_fn(state)
        return {"_state": result}
    return wrapped


async def run_procurement_workflow(requirements: UserRequirements) -> ProcurementWorkflowState:
    """
    Execute the full procurement pipeline for given requirements.
    
    Args:
        requirements: Structured user procurement requirements.
    
    Returns:
        Completed ProcurementWorkflowState with ranked vendors and explanation.
    """
    graph = build_procurement_graph()

    initial_state = ProcurementWorkflowState(user_requirements=requirements)
    
    try:
        result = await graph.ainvoke({"_state": initial_state})
        final_state: ProcurementWorkflowState = result["_state"]
    except VendorDiscoveryError as e:
        logger.error(f"[graph] Caught VendorDiscoveryError: {e}")
        final_state = ProcurementWorkflowState(user_requirements=requirements)
        final_state.error = str(e)
        return final_state

    logger.info(
        f"[graph] Workflow complete. "
        f"Vendors ranked: {len(final_state.ranked_vendors)}"
    )
    return final_state
