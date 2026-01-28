"""Tests for case drill-down engine."""

from datetime import datetime, timezone

from src.case_drilldown.case_drilldown_engine import CaseDrilldownEngine
from src.models.risk import BundleBreakRisk, RiskSeverity
from src.models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState


def build_risk() -> BundleBreakRisk:
    return BundleBreakRisk(
        risk_id="risk_case_1",
        bundle_id="bundle_1",
        assessment_timestamp=datetime.now(timezone.utc),
        model_version="1.0",
        break_probability=0.75,
        break_severity=RiskSeverity.HIGH,
        confidence_score=0.85,
        primary_drivers=[],
        secondary_drivers=[],
        bundle_size=2,
        bundle_health_score=0.4,
        timing_alignment_score=0.5,
        estimated_break_timeframe="3 days",
        critical_factors=[],
        recommendations=[],
    )


def build_snapshot() -> RefillSnapshot:
    now = datetime.now(timezone.utc)
    return RefillSnapshot(
        snapshot_id="snap_1",
        member_id="member_12345678",
        refill_id="refill_12345678",
        bundle_id="bundle_1",
        snapshot_timestamp=now,
        current_stage=SnapshotStage.BUNDLED,
        pa_state=PAState.NOT_REQUIRED,
        bundle_timing_state=BundleTimingState.ALIGNED,
        total_events=1,
        latest_event_timestamp=now,
        earliest_event_timestamp=now,
    )


def test_case_drilldown_creation():
    engine = CaseDrilldownEngine()
    risk = build_risk()
    snapshot = build_snapshot()

    case = engine.create_case(risk, snapshots=[snapshot])
    assert case.risk_id == risk.risk_id
    assert case.bundle_id == risk.bundle_id
    assert case.timeline
    assert "risk" in case.summary.lower()
