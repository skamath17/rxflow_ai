"""Tests for executive savings dashboard engine."""

from src.executive_dashboard.executive_dashboard_engine import ExecutiveSavingsDashboardEngine
from src.models.outcomes import BundleOutcome, OutcomeType


def build_outcome(shipments: int, outreach: int, savings: float) -> BundleOutcome:
    return BundleOutcome(
        outcome_id="outcome_1",
        action_id="action_1",
        recommendation_id="rec_1",
        outcome_type=OutcomeType.SHIPMENT_REDUCTION,
        shipments_reduced=shipments,
        outreach_suppressed=outreach,
        cost_savings_estimate=savings,
    )


def test_executive_dashboard_snapshot():
    engine = ExecutiveSavingsDashboardEngine()
    outcomes = [
        build_outcome(2, 3, 10.0),
        build_outcome(1, 2, 5.0),
    ]

    snapshot = engine.build_snapshot(outcomes)
    assert snapshot.total_shipments_reduced == 3
    assert snapshot.total_outreach_suppressed == 5
    assert snapshot.total_cost_savings == 15.0
    assert snapshot.outcomes_tracked == 2
