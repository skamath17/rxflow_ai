"""
Ops work queue engine for bundle risk follow-up.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..models.work_queue import BundleRiskQueueItem, QueuePriority, QueueItemStatus
from ..models.risk import BundleBreakRisk, RefillAbandonmentRisk


class OpsWorkQueueEngine:
    """Manage ops work queue entries for bundle risk follow-up."""

    def __init__(self):
        self._queue_items: Dict[str, BundleRiskQueueItem] = {}
        self._bundle_index: Dict[str, List[str]] = {}
        self._status_index: Dict[QueueItemStatus, List[str]] = {}

    def create_from_risk(
        self,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        priority: QueuePriority = QueuePriority.MEDIUM,
        assigned_to: Optional[str] = None,
    ) -> BundleRiskQueueItem:
        queue_id = f"queue_{uuid.uuid4().hex[:10]}"
        summary = self._build_summary(risk)
        item = BundleRiskQueueItem(
            queue_id=queue_id,
            risk_id=risk.risk_id,
            risk_type=risk.__class__.__name__,
            risk_severity=getattr(risk, "break_severity", getattr(risk, "abandonment_severity", "unknown")),
            bundle_id=getattr(risk, "bundle_id", None),
            member_id=getattr(risk, "member_id", None),
            refill_id=getattr(risk, "refill_id", None),
            title=self._build_title(risk),
            summary=summary,
            priority=priority,
            status=QueueItemStatus.OPEN,
            assigned_to=assigned_to,
            metadata={"confidence": getattr(risk, "confidence_score", None)},
        )
        self._queue_items[queue_id] = item
        if item.bundle_id:
            self._bundle_index.setdefault(item.bundle_id, []).append(queue_id)
        self._status_index.setdefault(item.status, []).append(queue_id)
        return item

    def update_status(
        self,
        queue_id: str,
        status: QueueItemStatus,
        assigned_to: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> BundleRiskQueueItem:
        item = self._queue_items[queue_id]
        if item.status != status:
            self._status_index.get(item.status, []).remove(queue_id)
            self._status_index.setdefault(status, []).append(queue_id)
        item.status = status
        if assigned_to is not None:
            item.assigned_to = assigned_to
        if notes:
            item.metadata.setdefault("notes", []).append(notes)
        item.updated_at = datetime.now(timezone.utc)
        return item

    def list_by_status(self, status: QueueItemStatus) -> List[BundleRiskQueueItem]:
        return [self._queue_items[qid] for qid in self._status_index.get(status, [])]

    def list_by_bundle(self, bundle_id: str) -> List[BundleRiskQueueItem]:
        return [self._queue_items[qid] for qid in self._bundle_index.get(bundle_id, [])]

    def get_item(self, queue_id: str) -> Optional[BundleRiskQueueItem]:
        return self._queue_items.get(queue_id)

    def _build_title(self, risk: BundleBreakRisk | RefillAbandonmentRisk) -> str:
        if isinstance(risk, BundleBreakRisk):
            return f"Bundle break risk for bundle {risk.bundle_id}"
        return f"Refill abandonment risk for refill {risk.refill_id}"

    def _build_summary(self, risk: BundleBreakRisk | RefillAbandonmentRisk) -> str:
        severity = getattr(risk, "break_severity", getattr(risk, "abandonment_severity", "unknown"))
        confidence = getattr(risk, "confidence_score", 0)
        return f"Severity {severity} with confidence {confidence:.2f}"
