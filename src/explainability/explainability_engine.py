"""
Explainability Engine for Bundle Risks.

Generates top-driver explanations with evidence and recommendation rationales
from risk assessments produced by the risk scoring engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from ..models.metrics import BundleMetrics
from ..models.risk import (
    BundleBreakRisk,
    RefillAbandonmentRisk,
    RiskDriver,
    RiskRecommendation,
    RiskSeverity,
    RiskType,
)
from ..models.explainability import (
    BundleRiskExplanation,
    ComparativeAnalysis,
    Evidence,
    EvidenceType,
    ExplanationList,
    ExplanationQuery,
    ExplanationType,
    ExplainabilityConfig,
    HistoricalContext,
    PredictiveInsights,
    RecommendationExplanation,
    RiskDriverExplanation,
    DriverImpact,
    VisualizationType,
)
from ..utils.version_registry import VersionRegistry
from ..models.versioning import VersionedArtifactType


class BundleRiskExplainabilityEngine:
    """Generates explainability artifacts for bundle risk assessments."""

    def __init__(
        self,
        config: Optional[ExplainabilityConfig] = None,
        version_registry: Optional[VersionRegistry] = None,
    ):
        self.config = config or ExplainabilityConfig()
        self.version_registry = version_registry or VersionRegistry()
        self._explanations: Dict[str, BundleRiskExplanation] = {}
        self._bundle_index: Dict[str, List[str]] = {}

    def explain_bundle_break(
        self,
        risk: BundleBreakRisk,
        metrics: BundleMetrics,
    ) -> BundleRiskExplanation:
        return self._build_explanation(
            risk_type=RiskType.BUNDLE_BREAK,
            risk_assessment=risk,
            metrics=metrics,
        )

    def explain_abandonment(
        self,
        risk: RefillAbandonmentRisk,
        metrics: BundleMetrics,
    ) -> BundleRiskExplanation:
        return self._build_explanation(
            risk_type=RiskType.REFILL_ABANDONMENT,
            risk_assessment=risk,
            metrics=metrics,
        )

    def get_explanation(self, explanation_id: str) -> Optional[BundleRiskExplanation]:
        return self._explanations.get(explanation_id)

    def query_explanations(self, query: ExplanationQuery) -> ExplanationList:
        items = list(self._explanations.values())

        if query.bundle_ids:
            items = [e for e in items if e.bundle_id in query.bundle_ids]
        if query.risk_types:
            items = [e for e in items if e.risk_type in query.risk_types]
        if query.confidence_threshold is not None:
            items = [e for e in items if e.overall_confidence >= query.confidence_threshold]

        total_count = len(items)
        start = query.offset
        end = query.offset + query.limit
        paged = items[start:end]

        return ExplanationList(
            explanations=paged,
            total_count=total_count,
            has_more=end < total_count,
            query_summary={
                "bundle_ids": query.bundle_ids,
                "risk_types": query.risk_types,
                "limit": query.limit,
                "offset": query.offset,
            },
        )

    def _build_explanation(
        self,
        risk_type: RiskType,
        risk_assessment: BundleBreakRisk | RefillAbandonmentRisk,
        metrics: BundleMetrics,
    ) -> BundleRiskExplanation:
        explanation_id = f"exp_{uuid.uuid4().hex[:10]}"
        primary_driver_explanations = self._explain_drivers(risk_assessment.primary_drivers)
        secondary_driver_explanations = self._explain_drivers(risk_assessment.secondary_drivers)
        recommendation_explanations = self._explain_recommendations(
            risk_assessment.recommendations,
            risk_assessment.primary_drivers,
        )

        executive_summary, key_takeaways = self._summarize_explanation(
            risk_type,
            risk_assessment,
            primary_driver_explanations,
        )
        overall_confidence = self._compute_overall_confidence(
            primary_driver_explanations,
            secondary_driver_explanations,
        )

        explanation = BundleRiskExplanation(
            explanation_id=explanation_id,
            bundle_id=getattr(risk_assessment, "bundle_id", "unknown"),
            risk_type=risk_type.value,
            risk_assessment_id=risk_assessment.risk_id,
            executive_summary=executive_summary,
            detailed_explanation=self._compose_detailed_explanation(primary_driver_explanations),
            key_takeaways=key_takeaways,
            primary_drivers=primary_driver_explanations,
            secondary_drivers=secondary_driver_explanations,
            recommendation_explanations=recommendation_explanations,
            overall_confidence=overall_confidence,
            explanation_completeness=self._compute_completeness(primary_driver_explanations),
            model_version=risk_assessment.model_version,
        )

        self._explanations[explanation_id] = explanation
        if explanation.bundle_id != "unknown":
            self._bundle_index.setdefault(explanation.bundle_id, []).append(explanation_id)

        self.version_registry.register(
            artifact_id=explanation_id,
            artifact_type=VersionedArtifactType.EXPLANATION,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            metadata={"risk_type": risk_type.value},
        )
        return explanation

    def _explain_drivers(self, drivers: List[RiskDriver]) -> List[RiskDriverExplanation]:
        ranked = sorted(drivers, key=lambda d: (d.impact_score, d.confidence), reverse=True)
        primary_limit = self.config.max_primary_drivers
        return [self._build_driver_explanation(d) for d in ranked[:primary_limit]]

    def _build_driver_explanation(self, driver: RiskDriver) -> RiskDriverExplanation:
        evidence = self._build_evidence(driver)
        impact_level = self._map_impact(driver.impact_score)
        narrative = (
            f"{driver.driver_name} contributes materially to risk due to "
            f"{self._describe_metric_evidence(driver.metric_values)}."
        )
        return RiskDriverExplanation(
            driver_id=f"drv_{uuid.uuid4().hex[:8]}",
            driver_name=driver.driver_name,
            driver_type=driver.driver_type.value,
            impact_level=impact_level,
            impact_score=driver.impact_score,
            confidence=driver.confidence,
            evidence=evidence,
            narrative=narrative,
            key_insights=self._derive_key_insights(driver, evidence),
            contributing_factors=list(driver.evidence.keys()) or [driver.driver_type.value],
            visualization_type=VisualizationType.BAR_CHART,
            visualization_data={"values": driver.metric_values},
            mitigation_potential=max(0.0, 1 - driver.impact_score),
            mitigation_difficulty="moderate" if driver.impact_score > 0.5 else "easy",
        )

    def _build_evidence(self, driver: RiskDriver) -> List[Evidence]:
        evidence_items: List[Evidence] = []
        for metric_name, metric_value in driver.metric_values.items():
            evidence_items.append(
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    evidence_type=EvidenceType.METRIC_VALUE,
                    description=f"{metric_name} observed value",
                    value=metric_value,
                    context={"metric": metric_name},
                    confidence=driver.confidence,
                    source="bundle_metrics",
                )
            )
        for evidence_key, evidence_val in driver.evidence.items():
            evidence_items.append(
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    evidence_type=EvidenceType.THRESHOLD_COMPARISON,
                    description=f"{evidence_key} evidence",
                    value=str(evidence_val),
                    context={"evidence_key": evidence_key},
                    confidence=driver.confidence,
                    source="risk_engine",
                )
            )
        return evidence_items[: self.config.max_evidence_per_driver]

    def _explain_recommendations(
        self,
        recommendations: List[RiskRecommendation],
        drivers: List[RiskDriver],
    ) -> List[RecommendationExplanation]:
        driver_ids = [d.driver_type.value for d in drivers]
        return [
            RecommendationExplanation(
                recommendation_id=rec.recommendation_id,
                recommendation_title=rec.title,
                recommendation_type=rec.category,
                priority=rec.priority,
                primary_rationale=rec.description,
                supporting_reasons=rec.action_steps or ["Mitigates key risk drivers."],
                expected_outcome=rec.expected_impact,
                supporting_evidence=[],
                success_probability=rec.success_probability or 0.7,
                implementation_complexity="moderate",
                resource_requirements=rec.required_resources,
                time_to_impact=rec.time_to_implement,
                risk_reduction_potential=0.6,
                affected_drivers=driver_ids,
            )
            for rec in recommendations
        ]

    def _summarize_explanation(
        self,
        risk_type: RiskType,
        risk: BundleBreakRisk | RefillAbandonmentRisk,
        driver_explanations: List[RiskDriverExplanation],
    ) -> Tuple[str, List[str]]:
        severity = getattr(risk, "break_severity", None) or getattr(risk, "abandonment_severity", None)
        top_drivers = ", ".join([d.driver_name for d in driver_explanations[:3]])
        executive_summary = (
            f"{risk_type.value.replace('_', ' ').title()} assessed as {severity.value if severity else 'unknown'} "
            f"driven primarily by {top_drivers or 'insufficient driver data'}."
        )
        key_takeaways = [
            f"Top drivers: {top_drivers}" if top_drivers else "No dominant drivers identified.",
            f"Confidence score: {getattr(risk, 'confidence_score', 0):.2f}",
        ]
        return executive_summary, key_takeaways

    def _compose_detailed_explanation(self, driver_explanations: List[RiskDriverExplanation]) -> str:
        if not driver_explanations:
            return "No driver explanations available due to limited data."
        lines = ["Drivers contributing to risk:"]
        for driver in driver_explanations:
            lines.append(f"- {driver.driver_name}: {driver.narrative}")
        return "\n".join(lines)

    def _derive_key_insights(self, driver: RiskDriver, evidence: List[Evidence]) -> List[str]:
        if not evidence:
            return ["Limited evidence available for this driver."]
        insights = [
            f"{driver.driver_name} impact score: {driver.impact_score:.2f}",
            f"Driver confidence: {driver.confidence:.2f}",
        ]
        for item in evidence[:2]:
            insights.append(f"Evidence: {item.description} = {item.value}")
        return insights

    def _compute_overall_confidence(
        self,
        primary: List[RiskDriverExplanation],
        secondary: List[RiskDriverExplanation],
    ) -> float:
        drivers = primary + secondary
        if not drivers:
            return 0.0
        avg_confidence = sum(d.confidence for d in drivers) / len(drivers)
        return round(avg_confidence, 3)

    def _compute_completeness(self, drivers: List[RiskDriverExplanation]) -> float:
        if not drivers:
            return 0.0
        evidence_counts = [len(d.evidence) for d in drivers]
        max_expected = self.config.max_evidence_per_driver
        ratio = sum(min(c, max_expected) for c in evidence_counts) / (len(drivers) * max_expected)
        return round(ratio, 3)

    @staticmethod
    def _map_impact(score: float) -> DriverImpact:
        if score >= 0.8:
            return DriverImpact.CRITICAL
        if score >= 0.6:
            return DriverImpact.HIGH
        if score >= 0.4:
            return DriverImpact.MEDIUM
        if score >= 0.2:
            return DriverImpact.LOW
        return DriverImpact.NEGLIGIBLE

    @staticmethod
    def _describe_metric_evidence(metric_values: Dict[str, float]) -> str:
        if not metric_values:
            return "limited metric evidence"
        top_metric = next(iter(metric_values.keys()))
        return f"{top_metric} metrics"
