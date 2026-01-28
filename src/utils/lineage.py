"""
Lineage completeness checks for event→snapshot→risk→action traceability.
"""

from __future__ import annotations

from typing import Iterable, Dict, Set

from ..models.lineage import LineageGap, LineageReport
from ..models.events import BaseCanonicalEvent
from ..models.snapshots import RefillSnapshot
from ..models.metrics import BundleMetrics
from ..models.recommendation import BundleRecommendation
from ..models.actions import TrackedAction
from ..models.outcomes import BundleOutcome


class LineageValidator:
    """Validate lineage completeness across pipeline artifacts."""

    def validate(
        self,
        events: Iterable[BaseCanonicalEvent],
        snapshots: Iterable[RefillSnapshot],
        metrics: Iterable[BundleMetrics],
        recommendations: Iterable[BundleRecommendation],
        actions: Iterable[TrackedAction],
        outcomes: Iterable[BundleOutcome],
    ) -> LineageReport:
        event_ids = {event.event_id for event in events}
        snapshot_ids = {snapshot.snapshot_id for snapshot in snapshots}
        metrics_ids = {metric.snapshot_id for metric in metrics}
        recommendation_ids = {rec.recommendation_id for rec in recommendations}
        action_ids = {action.action_id for action in actions}

        gaps = []
        gaps.extend(self._check_snapshot_events(snapshots, event_ids))
        gaps.extend(self._check_metrics_snapshots(metrics, snapshot_ids))
        gaps.extend(self._check_recommendations_metrics(recommendations, metrics_ids))
        gaps.extend(self._check_actions_recommendations(actions, recommendation_ids))
        gaps.extend(self._check_outcomes_actions(outcomes, action_ids))

        return LineageReport(
            is_complete=not gaps,
            gaps=gaps,
            total_events=len(event_ids),
            total_snapshots=len(snapshot_ids),
            total_metrics=len(metrics_ids),
            total_recommendations=len(recommendation_ids),
            total_actions=len(action_ids),
            total_outcomes=len({outcome.outcome_id for outcome in outcomes}),
        )

    @staticmethod
    def _check_snapshot_events(
        snapshots: Iterable[RefillSnapshot],
        event_ids: Set[str],
    ) -> list[LineageGap]:
        gaps = []
        for snapshot in snapshots:
            for event_id in snapshot.event_ids:
                if event_id not in event_ids:
                    gaps.append(
                        LineageGap(
                            stage="snapshot",
                            identifier=snapshot.snapshot_id,
                            message=f"Snapshot references missing event {event_id}",
                        )
                    )
        return gaps

    @staticmethod
    def _check_metrics_snapshots(
        metrics: Iterable[BundleMetrics],
        snapshot_ids: Set[str],
    ) -> list[LineageGap]:
        gaps = []
        for metric in metrics:
            if metric.snapshot_id not in snapshot_ids:
                gaps.append(
                    LineageGap(
                        stage="metrics",
                        identifier=metric.snapshot_id,
                        message="Metrics missing snapshot linkage",
                    )
                )
        return gaps

    @staticmethod
    def _check_recommendations_metrics(
        recommendations: Iterable[BundleRecommendation],
        metrics_ids: Set[str],
    ) -> list[LineageGap]:
        gaps = []
        for rec in recommendations:
            snapshot_id = rec.context.metrics_snapshot_id
            if snapshot_id and snapshot_id not in metrics_ids:
                gaps.append(
                    LineageGap(
                        stage="recommendation",
                        identifier=rec.recommendation_id,
                        message=f"Recommendation references missing metrics snapshot {snapshot_id}",
                    )
                )
        return gaps

    @staticmethod
    def _check_actions_recommendations(
        actions: Iterable[TrackedAction],
        recommendation_ids: Set[str],
    ) -> list[LineageGap]:
        gaps = []
        for action in actions:
            if action.recommendation_id not in recommendation_ids:
                gaps.append(
                    LineageGap(
                        stage="action",
                        identifier=action.action_id,
                        message=f"Action references missing recommendation {action.recommendation_id}",
                    )
                )
        return gaps

    @staticmethod
    def _check_outcomes_actions(
        outcomes: Iterable[BundleOutcome],
        action_ids: Set[str],
    ) -> list[LineageGap]:
        gaps = []
        for outcome in outcomes:
            if outcome.action_id not in action_ids:
                gaps.append(
                    LineageGap(
                        stage="outcome",
                        identifier=outcome.outcome_id,
                        message=f"Outcome references missing action {outcome.action_id}",
                    )
                )
        return gaps
