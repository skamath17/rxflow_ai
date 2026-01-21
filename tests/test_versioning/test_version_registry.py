"""Tests for version registry and engine integration."""

from datetime import datetime, timezone

from src.utils.version_registry import VersionRegistry
from src.models.versioning import VersionedArtifactType
from src.risk.risk_scoring_engine import BundleRiskScoringEngine
from src.explainability.explainability_engine import BundleRiskExplainabilityEngine
from src.models.metrics import (
    BundleMetrics,
    AgeInStageMetrics,
    TimingOverlapMetrics,
    RefillGapMetrics,
    BundleAlignmentMetrics,
    MetricSeverity,
)
from src.models.risk import RiskDriver, RiskDriverType, RiskRecommendation, RiskSeverity, BundleBreakRisk


def build_metrics(bundle_id: str) -> BundleMetrics:
    timestamp = datetime.now(timezone.utc)
    return BundleMetrics(
        snapshot_id="snap_v1",
        member_id="member_0001",
        refill_id="refill_0001",
        computed_timestamp=timestamp,
        metrics_version="1.0",
        age_in_stage=AgeInStageMetrics(
            current_stage="pa_pending",
            days_in_current_stage=3,
            stage_history={"initiated": 1},
            initiation_to_eligible_days=1,
            eligibility_to_bundled_days=None,
            bundled_to_shipped_days=None,
            is_aging_in_stage=False,
            stage_age_percentile=0.3,
        ),
        timing_overlap=TimingOverlapMetrics(
            bundle_id=bundle_id,
            bundle_size=1,
            refill_overlap_score=0.8,
            timing_variance_days=1.0,
            max_timing_gap_days=1,
            is_well_aligned=True,
            alignment_efficiency=0.9,
            fragmentation_risk=0.2,
            shipment_split_probability=0.1,
        ),
        refill_gap=RefillGapMetrics(
            days_since_last_fill=10,
            days_until_next_due=5,
            refill_gap_days=10,
            is_optimal_gap=True,
            gap_efficiency_score=0.8,
            abandonment_risk=0.2,
            urgency_score=0.3,
            days_supply_remaining=5,
            supply_buffer_days=3,
        ),
        bundle_alignment=BundleAlignmentMetrics(
            bundle_id=bundle_id,
            bundle_member_count=1,
            bundle_refill_count=1,
            bundle_alignment_score=0.8,
            timing_alignment_score=0.85,
            bundle_efficiency_score=0.9,
            cost_savings_potential=0.7,
            split_risk_score=0.2,
            outreach_reduction_score=0.6,
            bundle_health_score=0.85,
            recommended_actions=[],
        ),
        overall_risk_score=0.2,
        risk_severity=MetricSeverity.LOW,
        primary_risk_factors=[],
        requires_attention=False,
        recommended_actions=[],
        computation_time_ms=5,
    )


def build_risk(bundle_id: str) -> BundleBreakRisk:
    now = datetime.now(timezone.utc)
    driver = RiskDriver(
        driver_type=RiskDriverType.TIMING_MISALIGNMENT,
        driver_name="Timing Misalignment",
        impact_score=0.2,
        confidence=0.9,
        evidence={},
        metric_values={},
    )
    recommendation = RiskRecommendation(
        recommendation_id="rec_v1",
        priority="low",
        category="timing",
        title="Maintain alignment",
        description="Timing is healthy.",
        action_steps=[],
        expected_impact="Sustain bundle health",
        time_to_implement="n/a",
        success_probability=0.9,
        applicable_stages=[],
        required_resources=[],
    )
    return BundleBreakRisk(
        risk_id="risk_v1",
        bundle_id=bundle_id,
        assessment_timestamp=now,
        model_version="1.0",
        break_probability=0.2,
        break_severity=RiskSeverity.LOW,
        confidence_score=0.9,
        primary_drivers=[driver],
        secondary_drivers=[],
        bundle_size=1,
        bundle_health_score=0.85,
        timing_alignment_score=0.85,
        estimated_break_timeframe=None,
        critical_factors=[],
        recommendations=[recommendation],
    )


def test_version_registry_register():
    registry = VersionRegistry()
    record = registry.register(
        artifact_id="artifact_1",
        artifact_type=VersionedArtifactType.RISK_ASSESSMENT,
        model_name="risk_engine",
        model_version="1.0",
        metadata={"risk_type": "bundle_break"},
    )
    assert record.record_id
    assert record.artifact_id == "artifact_1"
    assert registry.list_by_artifact("artifact_1")
    assert registry.list_by_type(VersionedArtifactType.RISK_ASSESSMENT)


def test_version_registry_engine_integration():
    registry = VersionRegistry()
    risk_engine = BundleRiskScoringEngine(version_registry=registry)
    metrics = build_metrics("bundle_v1")
    risk = risk_engine.assess_bundle_break_risk(metrics)

    records = registry.list_by_artifact(risk.risk_id)
    assert records
    assert records[0].artifact_type == VersionedArtifactType.RISK_ASSESSMENT


def test_version_registry_explainability_integration():
    registry = VersionRegistry()
    explain_engine = BundleRiskExplainabilityEngine(version_registry=registry)
    metrics = build_metrics("bundle_v1")
    risk = build_risk("bundle_v1")

    explanation = explain_engine.explain_bundle_break(risk, metrics)

    records = registry.list_by_artifact(explanation.explanation_id)
    assert records
    assert records[0].artifact_type == VersionedArtifactType.EXPLANATION
