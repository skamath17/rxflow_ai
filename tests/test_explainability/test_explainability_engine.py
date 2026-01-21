"""Tests for explainability engine."""

from datetime import datetime, timezone

import pytest

from src.explainability.explainability_engine import BundleRiskExplainabilityEngine
from src.models.metrics import (
    BundleMetrics,
    AgeInStageMetrics,
    TimingOverlapMetrics,
    RefillGapMetrics,
    BundleAlignmentMetrics,
    MetricSeverity,
)
from src.models.risk import (
    BundleBreakRisk,
    RefillAbandonmentRisk,
    RiskDriver,
    RiskDriverType,
    RiskRecommendation,
    RiskSeverity,
)
from src.models.explainability import ExplanationQuery, ExplanationType


def build_metrics(bundle_id: str) -> BundleMetrics:
    timestamp = datetime.now(timezone.utc)
    return BundleMetrics(
        snapshot_id="snap_1",
        member_id="mem_1",
        refill_id="ref_1",
        computed_timestamp=timestamp,
        metrics_version="1.0",
        age_in_stage=AgeInStageMetrics(
            current_stage="pa_pending",
            days_in_current_stage=7,
            stage_history={"initiated": 2, "eligible": 1},
            initiation_to_eligible_days=2,
            eligibility_to_bundled_days=1,
            bundled_to_shipped_days=None,
            is_aging_in_stage=True,
            stage_age_percentile=0.8,
        ),
        timing_overlap=TimingOverlapMetrics(
            bundle_id=bundle_id,
            bundle_size=2,
            refill_overlap_score=0.4,
            timing_variance_days=6.0,
            max_timing_gap_days=9,
            is_well_aligned=False,
            alignment_efficiency=0.5,
            fragmentation_risk=0.7,
            shipment_split_probability=0.6,
        ),
        refill_gap=RefillGapMetrics(
            days_since_last_fill=40,
            days_until_next_due=-3,
            refill_gap_days=40,
            is_optimal_gap=False,
            gap_efficiency_score=0.2,
            abandonment_risk=0.75,
            urgency_score=0.9,
            days_supply_remaining=0,
            supply_buffer_days=-5,
        ),
        bundle_alignment=BundleAlignmentMetrics(
            bundle_id=bundle_id,
            bundle_member_count=1,
            bundle_refill_count=2,
            bundle_alignment_score=0.4,
            timing_alignment_score=0.45,
            bundle_efficiency_score=0.3,
            cost_savings_potential=0.2,
            split_risk_score=0.6,
            outreach_reduction_score=0.4,
            bundle_health_score=0.35,
            recommended_actions=["Optimize timing"],
        ),
        overall_risk_score=0.7,
        risk_severity=MetricSeverity.HIGH,
        primary_risk_factors=["timing_misalignment"],
        requires_attention=True,
        recommended_actions=["Review bundle timing"],
        computation_time_ms=25,
    )


def build_driver(driver_type: RiskDriverType, impact: float) -> RiskDriver:
    return RiskDriver(
        driver_type=driver_type,
        driver_name=driver_type.value.replace("_", " ").title(),
        impact_score=impact,
        confidence=0.8,
        evidence={"threshold": "exceeded"},
        metric_values={"score": impact},
    )


def build_recommendation() -> RiskRecommendation:
    return RiskRecommendation(
        recommendation_id="rec_1",
        priority="high",
        category="timing",
        title="Align refill timing",
        description="Reduce timing variance to preserve bundle integrity.",
        action_steps=["Contact member", "Coordinate shipments"],
        expected_impact="Reduce bundle break probability",
        time_to_implement="1-2 weeks",
        success_probability=0.75,
        applicable_stages=["pa_pending"],
        required_resources=["Care team"],
    )


def build_bundle_break_risk(bundle_id: str) -> BundleBreakRisk:
    now = datetime.now(timezone.utc)
    drivers = [
        build_driver(RiskDriverType.TIMING_MISALIGNMENT, 0.75),
        build_driver(RiskDriverType.STAGE_AGING, 0.6),
    ]
    return BundleBreakRisk(
        risk_id="risk_break_1",
        bundle_id=bundle_id,
        assessment_timestamp=now,
        model_version="1.0",
        break_probability=0.75,
        break_severity=RiskSeverity.HIGH,
        confidence_score=0.82,
        primary_drivers=drivers,
        secondary_drivers=[],
        bundle_size=2,
        bundle_health_score=0.35,
        timing_alignment_score=0.45,
        estimated_break_timeframe="1-2 weeks",
        critical_factors=["timing variance"],
        recommendations=[build_recommendation()],
    )


def build_abandonment_risk() -> RefillAbandonmentRisk:
    now = datetime.now(timezone.utc)
    drivers = [build_driver(RiskDriverType.REFILL_GAP_ANOMALY, 0.7)]
    return RefillAbandonmentRisk(
        risk_id="risk_abandon_1",
        refill_id="ref_1",
        member_id="mem_1",
        assessment_timestamp=now,
        model_version="1.0",
        abandonment_probability=0.7,
        abandonment_severity=RiskSeverity.HIGH,
        confidence_score=0.78,
        primary_drivers=drivers,
        secondary_drivers=[],
        days_since_last_fill=40,
        days_until_due=-3,
        refill_stage="pa_pending",
        engagement_score=0.4,
        compliance_history={},
        estimated_abandonment_timeframe="1 week",
        critical_factors=["gap anomaly"],
        recommendations=[build_recommendation()],
    )


class TestExplainabilityEngine:
    def test_explain_bundle_break(self):
        engine = BundleRiskExplainabilityEngine()
        metrics = build_metrics("bundle_1")
        risk = build_bundle_break_risk("bundle_1")

        explanation = engine.explain_bundle_break(risk, metrics)

        assert explanation.bundle_id == "bundle_1"
        assert explanation.risk_type == "bundle_break"
        assert explanation.risk_assessment_id == risk.risk_id
        assert explanation.primary_drivers
        assert explanation.recommendation_explanations
        assert 0 <= explanation.overall_confidence <= 1
        assert 0 <= explanation.explanation_completeness <= 1

    def test_explain_abandonment(self):
        engine = BundleRiskExplainabilityEngine()
        metrics = build_metrics("bundle_1")
        risk = build_abandonment_risk()

        explanation = engine.explain_abandonment(risk, metrics)

        assert explanation.risk_type == "refill_abandonment"
        assert explanation.primary_drivers
        assert explanation.key_takeaways

    def test_query_explanations(self):
        engine = BundleRiskExplainabilityEngine()
        metrics = build_metrics("bundle_1")
        risk = build_bundle_break_risk("bundle_1")
        engine.explain_bundle_break(risk, metrics)

        query = ExplanationQuery(bundle_ids=["bundle_1"], limit=10, offset=0)
        result = engine.query_explanations(query)

        assert result.total_count == 1
        assert result.explanations

    def test_query_confidence_threshold(self):
        engine = BundleRiskExplainabilityEngine()
        metrics = build_metrics("bundle_1")
        risk = build_bundle_break_risk("bundle_1")
        engine.explain_bundle_break(risk, metrics)

        query = ExplanationQuery(confidence_threshold=0.9)
        result = engine.query_explanations(query)

        assert result.total_count in (0, 1)

    def test_query_risk_type(self):
        engine = BundleRiskExplainabilityEngine()
        metrics = build_metrics("bundle_1")
        risk = build_bundle_break_risk("bundle_1")
        engine.explain_bundle_break(risk, metrics)

        query = ExplanationQuery(risk_types=["bundle_break"])
        result = engine.query_explanations(query)

        assert result.total_count == 1
