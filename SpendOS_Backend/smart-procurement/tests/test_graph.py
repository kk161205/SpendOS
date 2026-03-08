"""
Integration tests for the LangGraph procurement workflow.
Tests the full pipeline with mocked LLM calls and DB.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.graph.state import (
    ProcurementWorkflowState, VendorData, ScoredVendor, UserRequirements
)
from app.agents.cost_normalization import cost_normalization_node
from app.agents.scoring import scoring_node
from app.agents.ranking import ranking_node
from app.agents.explanation import explanation_node


def make_requirements(**kwargs) -> UserRequirements:
    return UserRequirements(
        product_name=kwargs.get("product_name", "Industrial Sensors"),
        product_category=kwargs.get("product_category", "electronics"),
        quantity=kwargs.get("quantity", 500),
        budget_usd=kwargs.get("budget_usd", 100_000),
        cost_weight=0.35,
        reliability_weight=0.40,
        risk_weight=0.25,
    )


def make_vendor_data(i: int) -> VendorData:
    return VendorData(
        vendor_id=f"v{i}",
        name=f"Vendor {i}",
        category="electronics",
        country="Germany",
        years_in_business=5 + i,
        price_per_unit_usd=100.0 + i * 20,
        average_rating=3.5 + (i * 0.1),
        on_time_delivery_rate=85.0 + i,
        certifications=["ISO 9001"] if i % 2 == 0 else [],
        financial_stability_score=60.0 + i * 2,
        negative_news_mentions=max(0, 3 - i),
        compliance_issues=max(0, 2 - i),
    )


def make_scored_vendor(i: int) -> ScoredVendor:
    return ScoredVendor(
        vendor_data=make_vendor_data(i),
        risk_score=40.0 - i * 3,
        reliability_score=60.0 + i * 4,
    )


class TestCostNormalizationIntegration:
    @pytest.mark.asyncio
    async def test_full_normalization_pipeline(self):
        """Cost normalization should assign scores such that cheapest = 100."""
        vendors = [make_scored_vendor(i) for i in range(1, 5)]
        req = make_requirements()
        state = ProcurementWorkflowState(
            user_requirements=req,
            scored_vendors=vendors,
        )
        result = await cost_normalization_node(state)
        scores = [sv.cost_score for sv in result.scored_vendors]
        # Cheapest is vendor 1 (price=120), most expensive is vendor 4 (price=180)
        assert max(scores) == pytest.approx(100.0)
        assert min(scores) == pytest.approx(0.0)


class TestScoringIntegration:
    @pytest.mark.asyncio
    async def test_full_scoring_flow(self):
        """After scoring, final scores should reflect the weighted formula."""
        vendors = [make_scored_vendor(i) for i in range(1, 4)]
        for sv in vendors:
            sv.cost_score = 70.0
        req = make_requirements()
        state = ProcurementWorkflowState(
            user_requirements=req,
            scored_vendors=vendors,
        )
        result = await scoring_node(state)
        for sv in result.scored_vendors:
            expected = (0.35 * sv.cost_score) + (0.40 * sv.reliability_score) - (0.25 * sv.risk_score)
            assert sv.final_score == pytest.approx(expected, rel=1e-4)


class TestRankingIntegration:
    @pytest.mark.asyncio
    async def test_ranking_assigns_sequential_ranks(self):
        """All vendors should have sequential ranks starting at 1."""
        vendors = [make_scored_vendor(i) for i in range(1, 6)]
        for i, sv in enumerate(vendors):
            sv.final_score = float((5 - i) * 10)
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            scored_vendors=vendors,
        )
        result = await ranking_node(state)
        ranks = [sv.rank for sv in result.ranked_vendors]
        assert ranks == list(range(1, 6))

    @pytest.mark.asyncio
    async def test_rank_1_has_highest_final_score(self):
        """Rank 1 vendor must have the highest final score."""
        vendors = [make_scored_vendor(i) for i in range(1, 4)]
        vendors[0].final_score = 50.0
        vendors[1].final_score = 90.0
        vendors[2].final_score = 70.0
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            scored_vendors=vendors,
        )
        result = await ranking_node(state)
        assert result.ranked_vendors[0].final_score == pytest.approx(90.0)
        assert result.ranked_vendors[0].rank == 1


class TestExplanationIntegration:
    @pytest.mark.asyncio
    async def test_explanation_falls_back_gracefully(self):
        """When LLM is unavailable, fallback explanation is returned."""
        vendors = [make_scored_vendor(i) for i in range(1, 3)]
        for i, sv in enumerate(vendors):
            sv.rank = i + 1
            sv.final_score = float(90 - i * 10)

        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            ranked_vendors=vendors,
        )

        with patch(
            "app.agents.explanation.invoke_llm",
            new_callable=AsyncMock,
            side_effect=Exception("LLM unavailable"),
        ):
            result = await explanation_node(state)

        assert "Vendor 1" in result.ai_explanation or "vendor" in result.ai_explanation.lower()
        assert result.ai_explanation != ""

    @pytest.mark.asyncio
    async def test_empty_vendors_returns_no_vendors_message(self):
        """With no vendors, explanation should indicate none found."""
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            ranked_vendors=[],
        )
        result = await explanation_node(state)
        assert "no vendors" in result.ai_explanation.lower()


class TestWorkflowStatePropagation:
    @pytest.mark.asyncio
    async def test_state_passes_through_deterministic_nodes(self):
        """Run cost_normalization → scoring → ranking in sequence, verify state propagation."""
        vendors = [make_scored_vendor(i) for i in range(1, 4)]
        req = make_requirements()
        state = ProcurementWorkflowState(
            user_requirements=req,
            scored_vendors=vendors,
        )

        state = await cost_normalization_node(state)
        state = await scoring_node(state)
        state = await ranking_node(state)

        assert len(state.ranked_vendors) == 3
        for sv in state.ranked_vendors:
            assert sv.rank > 0
            assert sv.cost_score >= 0
            assert sv.final_score != 0
