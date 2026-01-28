"""
Outcome tracking engine for bundle and outreach results.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..models.outcomes import BundleOutcome, OutcomeStatus, OutcomeSummary, OutcomeType
from ..models.actions import TrackedAction


class OutcomeTrackingEngine:
    """Track measured outcomes tied to actions and recommendations."""

    def __init__(self):
        self._outcomes: Dict[str, BundleOutcome] = {}
        self._action_index: Dict[str, List[str]] = {}

    def create_outcome(
        self,
        action: TrackedAction,
        outcome_type: OutcomeType,
        baseline_shipments: Optional[int] = None,
        baseline_outreach: Optional[int] = None,
        cost_savings_estimate: Optional[float] = None,
    ) -> BundleOutcome:
        outcome_id = f"outcome_{uuid.uuid4().hex[:10]}"
        outcome = BundleOutcome(
            outcome_id=outcome_id,
            action_id=action.action_id,
            recommendation_id=action.recommendation_id,
            outcome_type=outcome_type,
            status=OutcomeStatus.PENDING,
            bundle_id=action.bundle_id,
            member_id=action.member_id,
            refill_id=action.refill_id,
            baseline_shipments=baseline_shipments,
            baseline_outreach=baseline_outreach,
            cost_savings_estimate=cost_savings_estimate,
        )
        self._outcomes[outcome_id] = outcome
        self._action_index.setdefault(action.action_id, []).append(outcome_id)
        return outcome

    def record_measurement(
        self,
        outcome_id: str,
        actual_shipments: Optional[int] = None,
        actual_outreach: Optional[int] = None,
        cost_savings_estimate: Optional[float] = None,
        confirm: bool = False,
    ) -> BundleOutcome:
        outcome = self._outcomes[outcome_id]
        outcome.actual_shipments = actual_shipments if actual_shipments is not None else outcome.actual_shipments
        outcome.actual_outreach = actual_outreach if actual_outreach is not None else outcome.actual_outreach
        if cost_savings_estimate is not None:
            outcome.cost_savings_estimate = cost_savings_estimate

        if outcome.baseline_shipments is not None and outcome.actual_shipments is not None:
            outcome.shipments_reduced = max(0, outcome.baseline_shipments - outcome.actual_shipments)
        if outcome.baseline_outreach is not None and outcome.actual_outreach is not None:
            outcome.outreach_suppressed = max(0, outcome.baseline_outreach - outcome.actual_outreach)

        outcome.status = OutcomeStatus.CONFIRMED if confirm else OutcomeStatus.MEASURED
        outcome.updated_at = datetime.now(timezone.utc)
        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[BundleOutcome]:
        return self._outcomes.get(outcome_id)

    def list_by_action(self, action_id: str) -> List[BundleOutcome]:
        return [self._outcomes[outcome_id] for outcome_id in self._action_index.get(action_id, [])]

    def summarize(self) -> OutcomeSummary:
        total_outcomes = len(self._outcomes)
        shipment_total = sum(o.shipments_reduced or 0 for o in self._outcomes.values())
        outreach_total = sum(o.outreach_suppressed or 0 for o in self._outcomes.values())
        total_savings = sum(o.cost_savings_estimate or 0.0 for o in self._outcomes.values())
        return OutcomeSummary(
            total_outcomes=total_outcomes,
            shipment_reduction_total=shipment_total,
            outreach_suppression_total=outreach_total,
            total_cost_savings=total_savings,
        )
