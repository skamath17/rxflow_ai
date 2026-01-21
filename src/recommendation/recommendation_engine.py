"""
Bundle-aware recommendation engine.

Builds actionable recommendations from risk assessments and metrics, with
prioritization and deduplication.
"""

from __future__ import annotations

import uuid
from typing import List, Dict, Iterable

from ..models.risk import BundleBreakRisk, RefillAbandonmentRisk, RiskRecommendation, RiskSeverity
from ..models.metrics import BundleMetrics
from ..models.recommendation import (
    BundleRecommendation,
    RecommendationActionType,
    RecommendationPriority,
    RecommendationContext,
)


class BundleRecommendationEngine:
    """Generate bundle-aware recommendations from risks."""

    def __init__(self):
        self._recommendations: Dict[str, BundleRecommendation] = {}

    def from_risk_assessment(
        self,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        metrics: BundleMetrics,
    ) -> List[BundleRecommendation]:
        recommendations = [
            self._to_bundle_recommendation(rec, risk, metrics)
            for rec in risk.recommendations
        ]
        ranked = self._rank_recommendations(recommendations)
        deduped = self._dedupe_recommendations(ranked)
        for rec in deduped:
            self._recommendations[rec.recommendation_id] = rec
        return deduped

    def get(self, recommendation_id: str) -> BundleRecommendation | None:
        return self._recommendations.get(recommendation_id)

    @staticmethod
    def _to_bundle_recommendation(
        rec: RiskRecommendation,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        metrics: BundleMetrics,
    ) -> BundleRecommendation:
        action_type = BundleRecommendationEngine._infer_action_type(rec)
        priority = BundleRecommendationEngine._map_priority(rec.priority)
        context = RecommendationContext(
            bundle_id=getattr(risk, "bundle_id", None),
            member_id=getattr(risk, "member_id", metrics.member_id),
            refill_id=getattr(risk, "refill_id", metrics.refill_id),
            risk_type="bundle_break" if isinstance(risk, BundleBreakRisk) else "refill_abandonment",
            risk_severity=(
                getattr(risk, "break_severity", None) or getattr(risk, "abandonment_severity", None)
            ).value,
            metrics_snapshot_id=metrics.snapshot_id,
            notes={"category": rec.category},
        )
        return BundleRecommendation(
            recommendation_id=f"bundle_rec_{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            priority=priority,
            title=rec.title,
            description=rec.description,
            action_steps=rec.action_steps,
            expected_impact=rec.expected_impact,
            confidence_score=rec.success_probability or 0.7,
            time_to_implement=rec.time_to_implement,
            rationale=[rec.description],
            context=context,
        )

    @staticmethod
    def _infer_action_type(rec: RiskRecommendation) -> RecommendationActionType:
        category = rec.category.lower()
        title = rec.title.lower()
        if "suppress" in title or "suppress" in category:
            return RecommendationActionType.SUPPRESS
        if "advance" in title or "accelerate" in title:
            return RecommendationActionType.ADVANCE
        if "delay" in title or "defer" in title:
            return RecommendationActionType.DELAY
        if "outreach" in category or "engagement" in category:
            return RecommendationActionType.OUTREACH
        return RecommendationActionType.MONITOR

    @staticmethod
    def _map_priority(priority: str) -> RecommendationPriority:
        value = priority.lower()
        if value == "urgent":
            return RecommendationPriority.URGENT
        if value == "high":
            return RecommendationPriority.HIGH
        if value == "medium":
            return RecommendationPriority.MEDIUM
        return RecommendationPriority.LOW

    @staticmethod
    def _rank_recommendations(recommendations: Iterable[BundleRecommendation]) -> List[BundleRecommendation]:
        priority_order = {
            RecommendationPriority.URGENT: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
        }
        return sorted(
            recommendations,
            key=lambda r: (priority_order[r.priority], -r.confidence_score),
        )

    @staticmethod
    def _dedupe_recommendations(recommendations: Iterable[BundleRecommendation]) -> List[BundleRecommendation]:
        seen = set()
        deduped = []
        for rec in recommendations:
            signature = (rec.action_type, rec.title)
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(rec)
        return deduped
