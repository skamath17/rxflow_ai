"""Tests for ops work queue engine."""

from datetime import datetime, timezone

from src.ops_queue.ops_work_queue_engine import OpsWorkQueueEngine
from src.models.risk import BundleBreakRisk, RiskSeverity
from src.models.work_queue import QueueItemStatus, QueuePriority


def build_bundle_break_risk() -> BundleBreakRisk:
    return BundleBreakRisk(
        risk_id="risk_1",
        bundle_id="bundle_1",
        assessment_timestamp=datetime.now(timezone.utc),
        model_version="1.0",
        break_probability=0.7,
        break_severity=RiskSeverity.HIGH,
        confidence_score=0.8,
        primary_drivers=[],
        secondary_drivers=[],
        bundle_size=2,
        bundle_health_score=0.4,
        timing_alignment_score=0.5,
        estimated_break_timeframe="5 days",
        critical_factors=[],
        recommendations=[],
    )


def test_ops_queue_create_and_update():
    engine = OpsWorkQueueEngine()
    risk = build_bundle_break_risk()

    item = engine.create_from_risk(risk, priority=QueuePriority.HIGH, assigned_to="ops")
    assert item.status == QueueItemStatus.OPEN
    assert item.priority == QueuePriority.HIGH

    updated = engine.update_status(item.queue_id, QueueItemStatus.IN_PROGRESS, notes="Working")
    assert updated.status == QueueItemStatus.IN_PROGRESS

    items = engine.list_by_status(QueueItemStatus.IN_PROGRESS)
    assert items
    assert items[0].queue_id == item.queue_id
