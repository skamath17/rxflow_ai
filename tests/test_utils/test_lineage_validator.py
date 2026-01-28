"""Tests for lineage completeness validation."""

from datetime import datetime, timezone

from src.utils.lineage import LineageValidator
from src.models.events import RefillEvent, EventType, EventSource
from src.models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState
from src.models.metrics import (
    BundleMetrics,
    AgeInStageMetrics,
    TimingOverlapMetrics,
    RefillGapMetrics,
    BundleAlignmentMetrics,
    MetricSeverity,
)
from src.models.recommendation import (
    BundleRecommendation,
    RecommendationActionType,
    RecommendationPriority,
    RecommendationContext,
)
from src.models.actions import TrackedAction, ActionStatus, ActionOutcome
from src.models.outcomes import BundleOutcome, OutcomeType


def _sample_event(event_id: str = "evt_12345678"):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return RefillEvent(
        event_id=event_id,
        member_id="mem_12345678abcd",
        refill_id="ref_12345678abcd",
        bundle_id=None,
        event_type=EventType.REFILL_INITIATED,
        event_source=EventSource.CENTERSYNC,
        event_timestamp=now,
        received_timestamp=now,
        drug_ndc="123456789012",
        drug_name="TestDrug",
        days_supply=30,
        quantity=1.0,
        refill_status="pending",
        source_status="pending",
    )


def _sample_snapshot(snapshot_id: str, event_id: str):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return RefillSnapshot(
        snapshot_id=snapshot_id,
        member_id="mem_12345678abcd",
        refill_id="ref_12345678abcd",
        bundle_id=None,
        snapshot_timestamp=now,
        current_stage=SnapshotStage.INITIATED,
        pa_state=PAState.NOT_REQUIRED,
        bundle_timing_state=BundleTimingState.UNKNOWN,
        total_events=1,
        latest_event_timestamp=now,
        earliest_event_timestamp=now,
        event_ids=[event_id],
    )


def _sample_metrics(snapshot_id: str):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return BundleMetrics(
        snapshot_id=snapshot_id,
        member_id="mem_12345678abcd",
        refill_id="ref_12345678abcd",
        computed_timestamp=now,
        age_in_stage=AgeInStageMetrics(
            current_stage="initiated",
            days_in_current_stage=0,
            stage_history={},
            initiation_to_eligible_days=None,
            eligibility_to_bundled_days=None,
            bundled_to_shipped_days=None,
            is_aging_in_stage=False,
            stage_age_percentile=0.0,
        ),
        timing_overlap=TimingOverlapMetrics(
            bundle_id=None,
            bundle_size=1,
            refill_overlap_score=1.0,
            timing_variance_days=0.0,
            max_timing_gap_days=0,
            is_well_aligned=True,
            alignment_efficiency=1.0,
            fragmentation_risk=0.0,
            shipment_split_probability=0.0,
        ),
        refill_gap=RefillGapMetrics(
            days_since_last_fill=0,
            days_until_next_due=0,
            refill_gap_days=0,
            is_optimal_gap=True,
            gap_efficiency_score=1.0,
            abandonment_risk=0.0,
            urgency_score=0.0,
            days_supply_remaining=None,
            supply_buffer_days=None,
        ),
        bundle_alignment=BundleAlignmentMetrics(
            bundle_id=None,
            bundle_member_count=1,
            bundle_refill_count=1,
            bundle_alignment_score=1.0,
            timing_alignment_score=1.0,
            geographic_alignment_score=None,
            bundle_efficiency_score=1.0,
            cost_savings_potential=0.0,
            split_risk_score=0.0,
            outreach_reduction_score=0.0,
            bundle_health_score=1.0,
            recommended_actions=[],
        ),
        overall_risk_score=0.0,
        risk_severity=MetricSeverity.LOW,
        primary_risk_factors=[],
        requires_attention=False,
        recommended_actions=[],
        computation_time_ms=1,
    )


def _sample_recommendation(snapshot_id: str):
    return BundleRecommendation(
        recommendation_id="rec_123456",
        action_type=RecommendationActionType.MONITOR,
        priority=RecommendationPriority.LOW,
        title="Monitor",
        description="Monitor",
        action_steps=[],
        expected_impact="None",
        confidence_score=0.5,
        time_to_implement="1 day",
        rationale=[],
        context=RecommendationContext(metrics_snapshot_id=snapshot_id),
    )


def _sample_action(recommendation_id: str):
    return TrackedAction(
        action_id="action_123456",
        recommendation_id=recommendation_id,
        action_type="monitor",
        status=ActionStatus.PROPOSED,
        outcome=ActionOutcome.UNKNOWN,
    )


def _sample_outcome(action_id: str, recommendation_id: str):
    return BundleOutcome(
        outcome_id="outcome_123456",
        action_id=action_id,
        recommendation_id=recommendation_id,
        outcome_type=OutcomeType.SHIPMENT_REDUCTION,
    )


def test_lineage_complete():
    event = _sample_event()
    snapshot = _sample_snapshot("snapshot_1", event.event_id)
    metrics = _sample_metrics(snapshot.snapshot_id)
    recommendation = _sample_recommendation(metrics.snapshot_id)
    action = _sample_action(recommendation.recommendation_id)
    outcome = _sample_outcome(action.action_id, recommendation.recommendation_id)

    validator = LineageValidator()
    report = validator.validate(
        events=[event],
        snapshots=[snapshot],
        metrics=[metrics],
        recommendations=[recommendation],
        actions=[action],
        outcomes=[outcome],
    )

    assert report.is_complete is True
    assert report.gaps == []


def test_lineage_missing_snapshot_event():
    event = _sample_event()
    snapshot = _sample_snapshot("snapshot_1", "missing_event")

    validator = LineageValidator()
    report = validator.validate(
        events=[event],
        snapshots=[snapshot],
        metrics=[],
        recommendations=[],
        actions=[],
        outcomes=[],
    )

    assert report.is_complete is False
    assert any(gap.stage == "snapshot" for gap in report.gaps)
