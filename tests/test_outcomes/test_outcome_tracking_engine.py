"""Tests for outcome tracking engine."""

from src.outcomes.outcome_tracking_engine import OutcomeTrackingEngine
from src.models.actions import TrackedAction
from src.models.outcomes import OutcomeType, OutcomeStatus


def build_action(action_id: str, rec_id: str) -> TrackedAction:
    return TrackedAction(
        action_id=action_id,
        recommendation_id=rec_id,
        action_type="delay",
        bundle_id="bundle_1",
        member_id="member_1",
        refill_id="refill_1",
    )


def test_outcome_tracking_measurement_and_summary():
    engine = OutcomeTrackingEngine()
    action = build_action("action_1", "rec_1")

    outcome = engine.create_outcome(
        action,
        outcome_type=OutcomeType.SHIPMENT_REDUCTION,
        baseline_shipments=3,
        cost_savings_estimate=12.5,
    )
    assert outcome.status == OutcomeStatus.PENDING

    measured = engine.record_measurement(
        outcome.outcome_id,
        actual_shipments=1,
        confirm=True,
    )
    assert measured.status == OutcomeStatus.CONFIRMED
    assert measured.shipments_reduced == 2

    summary = engine.summarize()
    assert summary.total_outcomes == 1
    assert summary.shipment_reduction_total == 2
    assert summary.total_cost_savings == 12.5
