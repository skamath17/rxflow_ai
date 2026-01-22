"""Tests for action tracking engine."""

from src.actions.action_tracking_engine import ActionTrackingEngine
from src.models.recommendation import (
    BundleRecommendation,
    RecommendationActionType,
    RecommendationPriority,
    RecommendationContext,
)
from src.models.actions import ActionStatus, ActionOutcome


def build_recommendation(rec_id: str) -> BundleRecommendation:
    return BundleRecommendation(
        recommendation_id=rec_id,
        action_type=RecommendationActionType.DELAY,
        priority=RecommendationPriority.HIGH,
        title="Delay refill",
        description="Delay to preserve bundle",
        action_steps=["Adjust schedule"],
        expected_impact="Reduce split",
        confidence_score=0.8,
        time_to_implement="3 days",
        rationale=["Timing misalignment"],
        context=RecommendationContext(bundle_id="bundle_1", member_id="member_1"),
    )


def test_action_tracking_create_update():
    engine = ActionTrackingEngine()
    rec = build_recommendation("rec_action_1")

    action = engine.create_from_recommendation(rec, assigned_to="ops")
    assert action.recommendation_id == rec.recommendation_id
    assert action.status == ActionStatus.PROPOSED

    updated = engine.update_status(
        action.action_id,
        status=ActionStatus.COMPLETED,
        outcome=ActionOutcome.SUCCESS,
        notes="Completed",
    )
    assert updated.status == ActionStatus.COMPLETED
    assert updated.outcome == ActionOutcome.SUCCESS


def test_action_tracking_list_by_recommendation():
    engine = ActionTrackingEngine()
    rec = build_recommendation("rec_action_2")
    action = engine.create_from_recommendation(rec)

    actions = engine.list_by_recommendation(rec.recommendation_id)
    assert actions
    assert actions[0].action_id == action.action_id
