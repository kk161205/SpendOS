"""
Procurement LangGraph Workflow.
Assembles all agent nodes into a deterministic sequential pipeline.

Pipeline:
  vendor_discovery → vendor_enrichment → risk_analysis → reliability_analysis
  → cost_normalization → scoring → ranking → explanation
"""

import logging
import copy
import threading
from langgraph.graph import StateGraph, END

_compiled_graph = None
_graph_lock = threading.Lock()

def get_procurement_graph():
    """Return the cached compiled LangGraph, building it thread-safely if needed."""
    global _compiled_graph
    if _compiled_graph is None:
        with _graph_lock:
            if _compiled_graph is None:
                _compiled_graph = build_procurement_graph()
    return _compiled_graph
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
    graph.add_node("risk_analysis", _wrap(risk_analysis_node, output_key="risk_state"))
    graph.add_node("reliability_analysis", _wrap(reliability_analysis_node, output_key="rel_state"))
    graph.add_node("merge_analyses", merge_analyses_node)
    graph.add_node("cost_normalization", _wrap(cost_normalization_node))
    graph.add_node("scoring", _wrap(scoring_node))
    graph.add_node("ranking", _wrap(ranking_node))
    graph.add_node("explanation", _wrap(explanation_node))

    # Set entry point
    graph.set_entry_point("vendor_discovery")

    # Sequential edges
    graph.add_edge("vendor_discovery", "vendor_enrichment")
    
    # Fan out to parallel analyses
    graph.add_edge("vendor_enrichment", "risk_analysis")
    graph.add_edge("vendor_enrichment", "reliability_analysis")
    
    # Fan in to merge node
    graph.add_edge("risk_analysis", "merge_analyses")
    graph.add_edge("reliability_analysis", "merge_analyses")
    
    graph.add_edge("merge_analyses", "cost_normalization")
    graph.add_edge("cost_normalization", "scoring")
    graph.add_edge("scoring", "ranking")
    graph.add_edge("ranking", "explanation")
    graph.add_edge("explanation", END)

    return graph.compile()


def _wrap(node_fn, output_key="_state"):
    """
    Adapter: converts dict state ↔ ProcurementWorkflowState dataclass.
    Uses deepcopy to prevent parallel nodes from mutating shared state.
    """
    async def wrapped(state_dict: dict) -> dict:
        state = state_dict.get("_state")
        if state is None:
            state = ProcurementWorkflowState()
        
        # Deepcopy to avoid parallel shared state mutation conflicts
        state_copy = copy.deepcopy(state)
        result = await node_fn(state_copy)
        
        return {output_key: result}
    return wrapped

async def merge_analyses_node(state_dict: dict) -> dict:
    """Merges output from parallel risk and reliability nodes."""
    risk_state = state_dict.get("risk_state")
    rel_state = state_dict.get("rel_state")
    
    if risk_state and rel_state:
        merged_state = risk_state  # Base state
        for risk_sv in merged_state.scored_vendors:
            rel_sv = next((sv for sv in rel_state.scored_vendors 
                           if sv.vendor_data.vendor_id == risk_sv.vendor_data.vendor_id), None)
            if rel_sv:
                risk_sv.reliability_score = rel_sv.reliability_score
                risk_sv.reliability_reasoning = rel_sv.reliability_reasoning
                risk_sv.reliability_breakdown = rel_sv.reliability_breakdown
        return {"_state": merged_state}
    
    # Fallback if one failed or during testing
    return {"_state": risk_state or rel_state}


async def run_procurement_workflow(requirements: UserRequirements) -> ProcurementWorkflowState:
    """
    Execute the full procurement pipeline for given requirements.
    
    Args:
        requirements: Structured user procurement requirements.
    
    Returns:
        Completed ProcurementWorkflowState with ranked vendors and explanation.
    """
    graph = get_procurement_graph()

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
