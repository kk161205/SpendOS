"""
Procurement LangGraph Workflow.
Assembles all agent nodes into a deterministic sequential pipeline.

Pipeline:
  vendor_discovery → vendor_enrichment → risk_analysis → reliability_analysis
  → cost_normalization → scoring → ranking → explanation
"""

import logging
import copy
import asyncio
from langgraph.graph import StateGraph, END

_compiled_graph = None
_graph_lock = asyncio.Lock()

async def get_procurement_graph():
    """Return the cached compiled LangGraph, building it thread-safely if needed."""
    global _compiled_graph
    if _compiled_graph is None:
        async with _graph_lock:
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


def _should_continue(state_dict: dict) -> str:
    """Route to END if an error occurred or no data, otherwise continue."""
    state: ProcurementWorkflowState = state_dict.get("_state")
    if not state:
        return "end"

    if state.error:
        logger.error(f"[graph] Workflow halted at {state.current_node}: {state.error}")
        return "end"
        
    if state.current_node == "vendor_discovery" and not state.vendors:
        logger.warning("[graph] No vendors discovered. Halting workflow.")
        return "end"
        
    if state.current_node == "cost_normalization" and not state.scored_vendors:
        logger.warning("[graph] No scored vendors. Halting.")
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

    # Conditional edges using _should_continue
    graph.add_conditional_edges("vendor_discovery", _should_continue, {"continue": "vendor_enrichment", "end": END})
    graph.add_conditional_edges("vendor_enrichment", _should_continue, {"continue": "risk_analysis", "end": END})
    graph.add_conditional_edges("risk_analysis", _should_continue, {"continue": "reliability_analysis", "end": END})
    graph.add_conditional_edges("reliability_analysis", _should_continue, {"continue": "cost_normalization", "end": END})
    graph.add_conditional_edges("cost_normalization", _should_continue, {"continue": "scoring", "end": END})
    graph.add_conditional_edges("scoring", _should_continue, {"continue": "ranking", "end": END})
    graph.add_conditional_edges("ranking", _should_continue, {"continue": "explanation", "end": END})
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
        
        node_name = node_fn.__name__
        logger.info(f"[graph] Enter node: {node_name}")
        
        # Deepcopy to avoid parallel shared state mutation conflicts
        state_copy = copy.deepcopy(state)
        result = await node_fn(state_copy)
        
        logger.info(f"[graph] Exit node: {node_name}")
        return {output_key: result}
    return wrapped




async def run_procurement_workflow(requirements: UserRequirements) -> ProcurementWorkflowState:
    """
    Execute the full procurement pipeline for given requirements.
    
    Args:
        requirements: Structured user procurement requirements.
    
    Returns:
        Completed ProcurementWorkflowState with ranked vendors and explanation.
    """
    graph = await get_procurement_graph()

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
