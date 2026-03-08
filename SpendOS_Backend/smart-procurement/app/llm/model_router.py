"""
Model Router — maps each LangGraph node to its designated Groq model.
This centralizes model selection and makes it easy to swap models
without touching individual agent files.
"""

from enum import Enum
from dataclasses import dataclass
from app.config import get_settings

settings = get_settings()


class WorkflowNode(str, Enum):
    VENDOR_DISCOVERY = "vendor_discovery"
    VENDOR_ENRICHMENT = "vendor_enrichment"
    RISK_ANALYSIS = "risk_analysis"
    RELIABILITY_ANALYSIS = "reliability_analysis"
    EXPLANATION = "explanation"


@dataclass
class NodeModelConfig:
    model_name: str
    temperature: float


# ──────────────────────────────────────────────────────────────────────────────
# Node → Model mapping
# Different models are used per node to distribute Groq API token usage
# and avoid hitting per-model rate limits.
# ──────────────────────────────────────────────────────────────────────────────
NODE_MODEL_MAP: dict[WorkflowNode, NodeModelConfig] = {
    WorkflowNode.VENDOR_DISCOVERY: NodeModelConfig(
        model_name=settings.llm_vendor_discovery,
        temperature=settings.llm_temperature_discovery,
    ),
    WorkflowNode.VENDOR_ENRICHMENT: NodeModelConfig(
        model_name=settings.llm_vendor_enrichment,
        temperature=settings.llm_temperature_enrichment,
    ),
    WorkflowNode.RISK_ANALYSIS: NodeModelConfig(
        model_name=settings.llm_risk_analysis,
        temperature=settings.llm_temperature_risk,
    ),
    WorkflowNode.RELIABILITY_ANALYSIS: NodeModelConfig(
        model_name=settings.llm_reliability_analysis,
        temperature=settings.llm_temperature_reliability,
    ),
    WorkflowNode.EXPLANATION: NodeModelConfig(
        model_name=settings.llm_explanation,
        temperature=settings.llm_temperature_explanation,
    ),
}


def get_model_for_node(node: WorkflowNode) -> NodeModelConfig:
    """Return the model configuration for a given workflow node."""
    return NODE_MODEL_MAP[node]
