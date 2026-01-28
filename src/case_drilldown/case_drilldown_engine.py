"""
Case drill-down engine for bundle risk investigations.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from ..models.case_drilldown import BundleRiskCase, DrilldownTimelineEvent, CaseStatus
from ..models.risk import BundleBreakRisk, RefillAbandonmentRisk
from ..models.actions import TrackedAction
from ..models.outcomes import BundleOutcome
from ..models.recommendation import BundleRecommendation
from ..models.snapshots import RefillSnapshot


class CaseDrilldownEngine:
    """Build case drill-down views for bundle risk investigations."""

    def create_case(
        self,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        snapshots: Optional[List[RefillSnapshot]] = None,
        recommendations: Optional[List[BundleRecommendation]] = None,
        actions: Optional[List[TrackedAction]] = None,
        outcomes: Optional[List[BundleOutcome]] = None,
    ) -> BundleRiskCase:
        case_id = f"case_{uuid.uuid4().hex[:10]}"
        timeline = self._build_timeline(risk, snapshots or [])
        drivers = [driver.dict() for driver in getattr(risk, "primary_drivers", [])]
        drivers += [driver.dict() for driver in getattr(risk, "secondary_drivers", [])]
        recommendation_payload = [rec.dict() for rec in recommendations or []]
        action_payload = [action.dict() for action in actions or []]
        outcome_payload = [outcome.dict() for outcome in outcomes or []]
        summary = self._build_summary(risk, timeline, drivers)

        return BundleRiskCase(
            case_id=case_id,
            risk_id=risk.risk_id,
            risk_type=risk.__class__.__name__,
            severity=(getattr(risk, "break_severity", None) or getattr(risk, "abandonment_severity", None)).value,
            bundle_id=getattr(risk, "bundle_id", None),
            member_id=getattr(risk, "member_id", None),
            refill_id=getattr(risk, "refill_id", None),
            status=CaseStatus.OPEN,
            timeline=timeline,
            drivers=drivers,
            recommendations=recommendation_payload,
            actions=action_payload,
            outcomes=outcome_payload,
            summary=summary,
        )

    def _build_timeline(
        self,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        snapshots: List[RefillSnapshot],
    ) -> List[DrilldownTimelineEvent]:
        events: List[DrilldownTimelineEvent] = []
        if isinstance(risk, BundleBreakRisk):
            events.append(
                DrilldownTimelineEvent(
                    timestamp=risk.assessment_timestamp,
                    label="Bundle break risk assessed",
                    details={"probability": risk.break_probability},
                )
            )
        else:
            events.append(
                DrilldownTimelineEvent(
                    timestamp=risk.assessment_timestamp,
                    label="Refill abandonment risk assessed",
                    details={"probability": risk.abandonment_probability},
                )
            )

        for snapshot in snapshots:
            events.append(
                DrilldownTimelineEvent(
                    timestamp=snapshot.snapshot_timestamp,
                    label=f"Snapshot captured ({snapshot.current_stage.value})",
                    details={
                        "bundle_id": snapshot.bundle_id,
                        "stage": snapshot.current_stage.value,
                        "pa_state": snapshot.pa_state.value,
                        "bundle_timing_state": snapshot.bundle_timing_state.value,
                    },
                )
            )

        events.sort(key=lambda event: event.timestamp)
        return events

    def _build_summary(
        self,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        timeline: List[DrilldownTimelineEvent],
        drivers: List[dict],
    ) -> str:
        latest_event = timeline[-1].label if timeline else "No timeline events"
        primary_driver = drivers[0]["driver_name"] if drivers else "No primary driver"
        severity = getattr(risk, "break_severity", getattr(risk, "abandonment_severity", "unknown"))
        return f"{severity.value if hasattr(severity, 'value') else severity} risk with {primary_driver}; latest: {latest_event}."
