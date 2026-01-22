"""
Action tracking engine for bundle-preserving interventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..models.actions import TrackedAction, ActionStatus, ActionOutcome
from ..models.recommendation import BundleRecommendation


class ActionTrackingEngine:
    """Track recommendation actions through their lifecycle."""

    def __init__(self):
        self._actions: Dict[str, TrackedAction] = {}
        self._recommendation_index: Dict[str, List[str]] = {}

    def create_from_recommendation(
        self,
        recommendation: BundleRecommendation,
        assigned_to: Optional[str] = None,
    ) -> TrackedAction:
        action_id = f"action_{uuid.uuid4().hex[:10]}"
        action = TrackedAction(
            action_id=action_id,
            recommendation_id=recommendation.recommendation_id,
            action_type=recommendation.action_type.value,
            status=ActionStatus.PROPOSED,
            outcome=ActionOutcome.UNKNOWN,
            bundle_id=recommendation.context.bundle_id,
            member_id=recommendation.context.member_id,
            refill_id=recommendation.context.refill_id,
            assigned_to=assigned_to,
            metadata={"priority": recommendation.priority.value},
        )
        self._actions[action_id] = action
        self._recommendation_index.setdefault(recommendation.recommendation_id, []).append(action_id)
        return action

    def update_status(
        self,
        action_id: str,
        status: ActionStatus,
        outcome: Optional[ActionOutcome] = None,
        notes: Optional[str] = None,
    ) -> TrackedAction:
        action = self._actions[action_id]
        action.status = status
        if outcome:
            action.outcome = outcome
        if notes:
            action.metadata.setdefault("notes", []).append(notes)
        action.updated_at = datetime.now(timezone.utc)
        return action

    def get_action(self, action_id: str) -> Optional[TrackedAction]:
        return self._actions.get(action_id)

    def list_by_recommendation(self, recommendation_id: str) -> List[TrackedAction]:
        return [self._actions[action_id] for action_id in self._recommendation_index.get(recommendation_id, [])]

    def list_by_status(self, status: ActionStatus) -> List[TrackedAction]:
        return [action for action in self._actions.values() if action.status == status]
