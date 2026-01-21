"""Tests for recommendation guardrail engine."""

from src.guardrails.guardrail_engine import RecommendationGuardrailEngine
from src.models.recommendation import (
    BundleRecommendation,
    RecommendationActionType,
    RecommendationPriority,
    RecommendationContext,
)


def build_recommendation(rec_id: str) -> BundleRecommendation:
    return BundleRecommendation(
        recommendation_id=rec_id,
        action_type=RecommendationActionType.OUTREACH,
        priority=RecommendationPriority.HIGH,
        title="Proactive outreach",
        description="Contact member",
        action_steps=["Call member"],
        expected_impact="Reduce abandonment",
        confidence_score=0.8,
        time_to_implement="1 day",
        rationale=["Gap risk"],
        context=RecommendationContext(bundle_id="bundle_1"),
    )


def test_guardrail_submit_and_approve():
    engine = RecommendationGuardrailEngine()
    rec = build_recommendation("rec_1")

    decisions = engine.submit_for_review([rec])
    assert decisions[0].status.value == "pending"

    decision = engine.approve("rec_1", reviewer="ops_user", notes="ok")
    assert decision.status.value == "approved"
    assert decision.reviewer == "ops_user"


def test_guardrail_deny():
    engine = RecommendationGuardrailEngine()
    rec = build_recommendation("rec_2")
    engine.submit_for_review([rec])

    decision = engine.deny("rec_2", reviewer="ops_user", notes="not needed")
    assert decision.status.value == "denied"
