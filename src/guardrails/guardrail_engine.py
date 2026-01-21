"""
Recommendation guardrail engine enforcing human approval.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..models.guardrails import ApprovalDecision, ApprovalStatus
from ..models.recommendation import BundleRecommendation


class RecommendationGuardrailEngine:
    """Manage human approval flow for recommendations."""

    def __init__(self):
        self._decisions: Dict[str, ApprovalDecision] = {}

    def submit_for_review(self, recommendations: List[BundleRecommendation]) -> List[ApprovalDecision]:
        decisions = []
        for rec in recommendations:
            decision = self._decisions.get(rec.recommendation_id)
            if decision:
                decisions.append(decision)
                continue
            decision = ApprovalDecision(recommendation_id=rec.recommendation_id)
            self._decisions[rec.recommendation_id] = decision
            decisions.append(decision)
        return decisions

    def approve(self, recommendation_id: str, reviewer: str, notes: Optional[str] = None) -> ApprovalDecision:
        decision = self._get_or_create(recommendation_id)
        decision.status = ApprovalStatus.APPROVED
        decision.reviewer = reviewer
        decision.decision_notes = notes
        decision.decided_at = decision.decided_at or decision.created_at
        return decision

    def deny(self, recommendation_id: str, reviewer: str, notes: Optional[str] = None) -> ApprovalDecision:
        decision = self._get_or_create(recommendation_id)
        decision.status = ApprovalStatus.DENIED
        decision.reviewer = reviewer
        decision.decision_notes = notes
        decision.decided_at = decision.decided_at or decision.created_at
        return decision

    def pending(self) -> List[ApprovalDecision]:
        return [d for d in self._decisions.values() if d.status == ApprovalStatus.PENDING]

    def approved(self) -> List[ApprovalDecision]:
        return [d for d in self._decisions.values() if d.status == ApprovalStatus.APPROVED]

    def denied(self) -> List[ApprovalDecision]:
        return [d for d in self._decisions.values() if d.status == ApprovalStatus.DENIED]

    def get_decision(self, recommendation_id: str) -> Optional[ApprovalDecision]:
        return self._decisions.get(recommendation_id)

    def _get_or_create(self, recommendation_id: str) -> ApprovalDecision:
        decision = self._decisions.get(recommendation_id)
        if decision is None:
            decision = ApprovalDecision(recommendation_id=recommendation_id)
            self._decisions[recommendation_id] = decision
        return decision
