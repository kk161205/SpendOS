"""
Unit tests for vendor scoring logic.
Tests scoring, cost normalization, and ranking without DB or LLM.
"""

import pytest
import asyncio
from app.graph.state import (
    ProcurementWorkflowState, ScoredVendor, VendorData, UserRequirements
)
from app.agents.cost_normalization import cost_normalization_node, _effective_price
from app.agents.scoring import scoring_node
from app.agents.ranking import ranking_node
from app.agents.risk_analysis import _heuristic_risk_score
from app.agents.reliability_analysis import _heuristic_reliability_score


def make_vendor(vendor_id: str, name: str, price: float, years: int = 5) -> VendorData:
    return VendorData(
        vendor_id=vendor_id,
        name=name,
        category="electronics",
        years_in_business=years,
        price_per_unit_usd=price,
        average_rating=4.0,
        on_time_delivery_rate=90.0,
        certifications=["ISO 9001"],
    )


def make_scored_vendor(vendor: VendorData, risk=30.0, reliability=70.0) -> ScoredVendor:
    return ScoredVendor(
        vendor_data=vendor,
        risk_score=risk,
        reliability_score=reliability,
    )


def make_requirements(**kwargs) -> UserRequirements:
    defaults = dict(
        product_name="Test Product",
        product_category="electronics",
        quantity=100,
        budget_usd=50_000,
        cost_weight=0.35,
        reliability_weight=0.40,
        risk_weight=0.25,
    )
    defaults.update(kwargs)
    return UserRequirements(**defaults)


# ── Cost Normalization ─────────────────────────────────────────────────────────

class TestCostNormalization:
    @pytest.mark.asyncio
    async def test_cheapest_vendor_gets_highest_cost_score(self):
        vendors = [
            make_scored_vendor(make_vendor("v1", "Cheap Corp", 10.0)),
            make_scored_vendor(make_vendor("v2", "Mid Corp", 50.0)),
            make_scored_vendor(make_vendor("v3", "Expensive Corp", 100.0)),
        ]
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            scored_vendors=vendors,
        )
        result = await cost_normalization_node(state)
        scores = {sv.vendor_data.name: sv.cost_score for sv in result.scored_vendors}

        assert scores["Cheap Corp"] > scores["Mid Corp"] > scores["Expensive Corp"]
        assert scores["Cheap Corp"] == pytest.approx(100.0)
        assert scores["Expensive Corp"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_single_vendor_gets_100_cost_score(self):
        vendors = [make_scored_vendor(make_vendor("v1", "Solo Corp", 42.0))]
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            scored_vendors=vendors,
        )
        result = await cost_normalization_node(state)
        assert result.scored_vendors[0].cost_score == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_over_budget_vendor_gets_penalty(self):
        # Quantity=100, price=600, total=60,000 > budget 50,000
        vendor = make_scored_vendor(make_vendor("v1", "Pricey Corp", 600.0))
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(quantity=100, budget_usd=50_000),
            scored_vendors=[vendor],
        )
        result = await cost_normalization_node(state)
        bd = result.scored_vendors[0].cost_breakdown
        assert bd["within_budget"] is False

    def test_effective_price_uses_unit_price_first(self):
        sv = make_scored_vendor(make_vendor("v1", "Corp", 10.0))
        sv.vendor_data.base_price_usd = 999.0  # Should not be used
        sv.vendor_data.price_per_unit_usd = 10.0
        assert _effective_price(sv, 100) == 10.0

    def test_effective_price_falls_back_to_base(self):
        sv = make_scored_vendor(make_vendor("v1", "Corp", 0.0))
        sv.vendor_data.price_per_unit_usd = None
        sv.vendor_data.base_price_usd = 25.0
        assert _effective_price(sv, 100) == 25.0


# ── Scoring ────────────────────────────────────────────────────────────────────

class TestScoring:
    @pytest.mark.asyncio
    async def test_final_score_formula(self):
        sv = make_scored_vendor(make_vendor("v1", "Corp", 50.0))
        sv.cost_score = 80.0
        sv.reliability_score = 70.0
        sv.risk_score = 20.0
        req = make_requirements(cost_weight=0.35, reliability_weight=0.40, risk_weight=0.25)
        state = ProcurementWorkflowState(
            user_requirements=req,
            scored_vendors=[sv],
        )
        result = await scoring_node(state)
        expected = (0.35 * 80) + (0.40 * 70) - (0.25 * 20)
        assert result.scored_vendors[0].final_score == pytest.approx(expected, rel=1e-4)

    @pytest.mark.asyncio
    async def test_high_risk_lowers_final_score(self):
        sv_safe = make_scored_vendor(make_vendor("v1", "Safe Corp", 50.0), risk=10.0, reliability=70.0)
        sv_risky = make_scored_vendor(make_vendor("v2", "Risky Corp", 50.0), risk=90.0, reliability=70.0)
        sv_safe.cost_score = 70.0
        sv_risky.cost_score = 70.0
        req = make_requirements()
        state = ProcurementWorkflowState(
            user_requirements=req,
            scored_vendors=[sv_safe, sv_risky],
        )
        result = await scoring_node(state)
        scores = {sv.vendor_data.name: sv.final_score for sv in result.scored_vendors}
        assert scores["Safe Corp"] > scores["Risky Corp"]


# ── Ranking ────────────────────────────────────────────────────────────────────

class TestRanking:
    @pytest.mark.asyncio
    async def test_vendors_sorted_by_final_score_descending(self):
        v1 = make_scored_vendor(make_vendor("v1", "Third", 50.0))
        v2 = make_scored_vendor(make_vendor("v2", "First", 50.0))
        v3 = make_scored_vendor(make_vendor("v3", "Second", 50.0))
        v1.final_score = 60.0
        v2.final_score = 90.0
        v3.final_score = 75.0
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            scored_vendors=[v1, v2, v3],
        )
        result = await ranking_node(state)
        names = [sv.vendor_data.name for sv in result.ranked_vendors]
        assert names == ["First", "Second", "Third"]

    @pytest.mark.asyncio
    async def test_ranks_assigned_correctly(self):
        vendors = [
            make_scored_vendor(make_vendor(f"v{i}", f"V{i}", 50.0))
            for i in range(1, 5)
        ]
        for i, sv in enumerate(vendors):
            sv.final_score = float(i * 10)
        state = ProcurementWorkflowState(
            user_requirements=make_requirements(),
            scored_vendors=vendors,
        )
        result = await ranking_node(state)
        ranks = [sv.rank for sv in result.ranked_vendors]
        assert ranks == [1, 2, 3, 4]


# ── Heuristic Risk ─────────────────────────────────────────────────────────────

class TestHeuristicRisk:
    def test_compliant_established_vendor_has_low_risk(self):
        v = make_vendor("v1", "Stable Corp", 50.0, years=20)
        v.compliance_issues = 0
        v.negative_news_mentions = 0
        v.financial_stability_score = 90.0
        score = _heuristic_risk_score(v)
        assert score < 50

    def test_new_vendor_with_issues_has_high_risk(self):
        v = make_vendor("v1", "Risky Corp", 50.0, years=1)
        v.compliance_issues = 4
        v.negative_news_mentions = 8
        v.financial_stability_score = 20.0
        score = _heuristic_risk_score(v)
        assert score > 60

    def test_risk_score_clamped_0_100(self):
        v = make_vendor("v1", "Corp", 50.0)
        v.compliance_issues = 999
        v.negative_news_mentions = 999
        score = _heuristic_risk_score(v)
        assert 0 <= score <= 100


# ── Heuristic Reliability ──────────────────────────────────────────────────────

class TestHeuristicReliability:
    def test_high_performing_vendor_reliable(self):
        v = make_vendor("v1", "Reliable Corp", 50.0, years=15)
        v.average_rating = 4.8
        v.on_time_delivery_rate = 98.0
        v.certifications = ["ISO 9001", "ISO 14001", "CE Mark"]
        score = _heuristic_reliability_score(v)
        assert score > 70

    def test_new_uncertified_vendor_low_reliability(self):
        v = make_vendor("v1", "New Corp", 50.0, years=1)
        v.average_rating = 2.0
        v.on_time_delivery_rate = 55.0
        v.certifications = []
        score = _heuristic_reliability_score(v)
        assert score <= 60

    def test_reliability_score_clamped_0_100(self):
        v = make_vendor("v1", "Corp", 50.0, years=100)
        v.average_rating = 5.0
        v.on_time_delivery_rate = 100.0
        v.certifications = ["C1", "C2", "C3", "C4", "C5"]
        score = _heuristic_reliability_score(v)
        assert 0 <= score <= 100
