"""
Integration test for the full sequential LangGraph workflow.
Replaces the core LLM Groq and SerpAPI interfaces to ensure the 
LangGraph state machine logic passes data smoothly end-to-end.
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.graph.procurement_graph import run_procurement_workflow
from app.graph.state import UserRequirements, VendorData

@pytest.fixture
def sample_requirements():
    return UserRequirements(
        product_name="Lithium Battery Pack 100Ah",
        product_category="electronics",
        quantity=500,
        budget_usd=100000,
        cost_weight=0.35,
        reliability_weight=0.40,
        risk_weight=0.25,
    )

@pytest.mark.asyncio
async def test_end_to_end_sequential_workflow(sample_requirements):
    # Mock Vendor Discovery (SerpAPI returned payload)
    mock_discovery = [
        {"vendor_id": "v1", "name": "PowerTech Inc", "url": "powertech.com"},
        {"vendor_id": "v2", "name": "GlobalBatteries", "url": "gb.com"}
    ]

    # Mock Enrichment
    async def mock_enrichment_call(vendor: VendorData):
        vendor.years_in_business = 10
        vendor.employee_count = 500
        vendor.base_price_usd = 15000.0
        return vendor

    # Mock Risk
    async def mock_risk_call(*args, **kwargs):
        return 20.0, "Low risk due to local presence", {"geopolitical": 10, "financial": 10}

    # Mock Reliability
    async def mock_reliability_call(*args, **kwargs):
        return 85.0, "Strong track record", {"delivery": 40, "quality": 45}

    # Mock Explanation
    mock_explanation = "Based on custom analysis, PowerTech Inc is the best option."

    with patch("app.agents.vendor_discovery._search_vendors", new_callable=AsyncMock, return_value=mock_discovery), \
         patch("app.agents.vendor_enrichment._enrich_vendor", new_callable=AsyncMock, side_effect=mock_enrichment_call), \
         patch("app.agents.risk_analysis._analyze_risk", new_callable=AsyncMock, side_effect=mock_risk_call), \
         patch("app.agents.reliability_analysis._analyze_reliability", new_callable=AsyncMock, side_effect=mock_reliability_call), \
         patch("app.agents.explanation.invoke_llm", new_callable=AsyncMock, return_value=mock_explanation):

        final_state = await run_procurement_workflow(sample_requirements)

        # Asserts
        assert final_state.error is None
        assert len(final_state.ranked_vendors) == 2
        
        v1 = final_state.ranked_vendors[0]
        assert v1.vendor_data.name == "PowerTech Inc"
        assert v1.risk_score == 20.0
        assert v1.reliability_score == 85.0
        assert v1.cost_score == 100.0  # Normalized since they all have the same mock price!
        assert v1.rank == 1

        assert final_state.ai_explanation == mock_explanation
