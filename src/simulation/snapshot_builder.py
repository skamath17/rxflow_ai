"""
Helpers to derive snapshots and metrics from synthetic events.
"""

from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from ..models.events import BaseCanonicalEvent, EventType
from ..models.metrics import (
    AgeInStageMetrics,
    BundleAlignmentMetrics,
    BundleMetrics,
    MetricSeverity,
    RefillGapMetrics,
    TimingOverlapMetrics,
)
from ..models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState


def build_snapshot(events: Iterable[BaseCanonicalEvent]) -> RefillSnapshot:
    events_list = list(events)
    if not events_list:
        raise ValueError("No events provided")

    latest_event = max(events_list, key=lambda event: event.event_timestamp)
    earliest_event = min(events_list, key=lambda event: event.event_timestamp)

    bundle_id = latest_event.bundle_id
    member_id = latest_event.member_id
    refill_id = latest_event.refill_id

    if any(event.event_type == EventType.REFILL_SHIPPED for event in events_list):
        stage = SnapshotStage.SHIPPED
    elif any(event.event_type == EventType.REFILL_BUNDLED for event in events_list):
        stage = SnapshotStage.BUNDLED
    elif any(event.event_type == EventType.REFILL_ELIGIBLE for event in events_list):
        stage = SnapshotStage.ELIGIBLE
    else:
        stage = SnapshotStage.INITIATED

    pa_state = PAState.NOT_REQUIRED
    if any(event.event_type == EventType.PA_SUBMITTED for event in events_list):
        pa_state = PAState.PENDING

    bundle_timing_state = BundleTimingState.ALIGNED
    if any(event.event_type == EventType.BUNDLE_SPLIT for event in events_list):
        bundle_timing_state = BundleTimingState.MISALIGNED

    return RefillSnapshot(
        snapshot_id=f"snapshot_{refill_id}",
        member_id=member_id,
        refill_id=refill_id,
        bundle_id=bundle_id,
        snapshot_timestamp=latest_event.event_timestamp,
        current_stage=stage,
        pa_state=pa_state,
        bundle_timing_state=bundle_timing_state,
        total_events=len(events_list),
        latest_event_timestamp=latest_event.event_timestamp,
        earliest_event_timestamp=earliest_event.event_timestamp,
        refill_events=len([e for e in events_list if e.event_type.value.startswith("refill")]),
        pa_events=len([e for e in events_list if e.event_type.value.startswith("pa")]),
        oos_events=len([e for e in events_list if e.event_type.value.startswith("oos")]),
        bundle_events=len([e for e in events_list if e.event_type.value.startswith("bundle")]),
        initiated_timestamp=earliest_event.event_timestamp,
    )


def build_metrics(events: Iterable[BaseCanonicalEvent]) -> BundleMetrics:
    events_list = list(events)
    snapshot = build_snapshot(events_list)
    bundle_health = 0.8 if snapshot.bundle_timing_state == BundleTimingState.ALIGNED else 0.4
    alignment_score = 0.8 if snapshot.bundle_timing_state == BundleTimingState.ALIGNED else 0.4

    age_metrics = AgeInStageMetrics(
        current_stage=snapshot.current_stage.value,
        days_in_current_stage=3,
        stage_history={snapshot.current_stage.value: 3},
        is_aging_in_stage=False,
        stage_age_percentile=0.3,
    )

    timing_metrics = TimingOverlapMetrics(
        bundle_id=snapshot.bundle_id,
        bundle_size=max(1, snapshot.bundle_refill_count or 1),
        refill_overlap_score=alignment_score,
        timing_variance_days=2.0 if alignment_score > 0.6 else 6.0,
        max_timing_gap_days=2 if alignment_score > 0.6 else 7,
        is_well_aligned=alignment_score > 0.6,
        alignment_efficiency=alignment_score,
        fragmentation_risk=1.0 - alignment_score,
        shipment_split_probability=1.0 - alignment_score,
    )

    gap_metrics = RefillGapMetrics(
        days_since_last_fill=20,
        days_until_next_due=10,
        refill_gap_days=30,
        is_optimal_gap=alignment_score > 0.6,
        gap_efficiency_score=alignment_score,
        abandonment_risk=0.2 if alignment_score > 0.6 else 0.6,
        urgency_score=0.3 if alignment_score > 0.6 else 0.7,
        days_supply_remaining=10,
        supply_buffer_days=5,
    )

    alignment_metrics = BundleAlignmentMetrics(
        bundle_id=snapshot.bundle_id,
        bundle_member_count=1,
        bundle_refill_count=1,
        bundle_alignment_score=alignment_score,
        timing_alignment_score=alignment_score,
        geographic_alignment_score=None,
        bundle_efficiency_score=alignment_score,
        cost_savings_potential=alignment_score * 0.5,
        split_risk_score=1.0 - alignment_score,
        outreach_reduction_score=alignment_score * 0.4,
        bundle_health_score=bundle_health,
        recommended_actions=[],
    )

    return BundleMetrics(
        snapshot_id=snapshot.snapshot_id,
        member_id=snapshot.member_id,
        refill_id=snapshot.refill_id,
        computed_timestamp=datetime.now(timezone.utc),
        age_in_stage=age_metrics,
        timing_overlap=timing_metrics,
        refill_gap=gap_metrics,
        bundle_alignment=alignment_metrics,
        overall_risk_score=1.0 - alignment_score,
        risk_severity=MetricSeverity.HIGH if alignment_score < 0.6 else MetricSeverity.LOW,
        primary_risk_factors=["bundle_alignment"],
        requires_attention=alignment_score < 0.6,
        recommended_actions=[],
        computation_time_ms=5,
    )


def build_snapshot_and_metrics(
    events: Iterable[BaseCanonicalEvent],
) -> Tuple[RefillSnapshot, BundleMetrics]:
    snapshot = build_snapshot(events)
    metrics = build_metrics(events)
    return snapshot, metrics
