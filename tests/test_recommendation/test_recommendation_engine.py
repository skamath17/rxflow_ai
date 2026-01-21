"""Tests for bundle recommendation engine."""

from datetime import datetime, timezone

from src.recommendation.recommendation_engine import BundleRecommendationEngine
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
    RiskRecommendation,
    RiskSeverity,
    RiskDriver,
    RiskDriverType,
)


def build_metrics(bundle_id: str) -> BundleMetrics:
    timestamp = datetime.now(timezone.utc)
    return BundleMetrics(
        snapshot_id="snap_rec_1",
        member_id="member_0001",
        refill_id="refill_0001",
        computed_timestamp=timestamp,
        metrics_version="1.0",
        age_in_stage=AgeInStageMetrics(
            current_stage="eligible",
            days_in_current_stage=2,
            stage_history={"initiated": 1},
            initiation_to_eligible_days=1,
            eligibility_to_bundled_days=None,
            bundled_to_shipped_days=None,
            is_aging_in_stage=False,
            stage_age_percentile=0.4,
        ),
        timing_overlap=TimingOverlapMetrics(
            bundle_id=bundle_id,
            bundle_size=2,
            refill_overlap_score=0.5,
            timing_variance_days=4.0,
            max_timing_gap_days=6,
            is_well_aligned=False,
            alignment_efficiency=0.6,
            fragmentation_risk=0.6,
            shipment_split_probability=0.4,
        ),
        refill_gap=RefillGapMetrics(
            days_since_last_fill=15,
            days_until_next_due=10,
            refill_gap_days=15,
            is_optimal_gap=True,
            gap_efficiency_score=0.7,
            abandonment_risk=0.3,
            urgency_score=0.4,
            days_supply_remaining=10,
            supply_buffer_days=5,
        ),
        bundle_alignment=BundleAlignmentMetrics(
            bundle_id=bundle_id,
            bundle_member_count=1,
            bundle_refill_count=2,
            bundle_alignment_score=0.6,
            timing_alignment_score=0.6,
            bundle_efficiency_score=0.6,
            cost_savings_potential=0.4,
            split_risk_score=0.5,
            outreach_reduction_score=0.5,
            bundle_health_score=0.6,
            recommended_actions=[],
        ),
        overall_risk_score=0.5,
        risk_severity=MetricSeverity.MEDIUM,
        primary_risk_factors=[],
        requires_attention=False,
        recommended_actions=[],
        computation_time_ms=5,
    )


def build_recommendation(title: str, priority: str, category: str) -> RiskRecommendation:
    return RiskRecommendation(
        recommendation_id=f"rec_{title}",
        priority=priority,
        category=category,
        title=title,
        description="Test description",
        action_steps=["Step 1"],
        expected_impact="Reduce risk",
        time_to_implement="2 days",
        success_probability=0.8,
        applicable_stages=["eligible"],
        required_resources=["Care team"],
    )


def build_risk(bundle_id: str) -> BundleBreakRisk:
    now = datetime.now(timezone.utc)
    driver = RiskDriver(
        driver_type=RiskDriverType.TIMING_MISALIGNMENT,
        driver_name="Timing Misalignment",
        impact_score=0.7,
        confidence=0.8,
        evidence={},
        metric_values={},
    )
    recs = [
        build_recommendation("Optimize Bundle Timing", "high", "timing_optimization"),
        build_recommendation("Optimize Bundle Timing", "medium", "timing_optimization"),
        build_recommendation("Proactive Outreach", "urgent", "member_engagement"),
    ]
    return BundleBreakRisk(
        risk_id="risk_rec_1",
        bundle_id=bundle_id,
        assessment_timestamp=now,
        model_version="1.0",
        break_probability=0.7,
        break_severity=RiskSeverity.HIGH,
        confidence_score=0.8,
        primary_drivers=[driver],
        secondary_drivers=[],
        bundle_size=2,
        bundle_health_score=0.6,
        timing_alignment_score=0.6,
        estimated_break_timeframe="1 week",
        critical_factors=[],
        recommendations=recs,
    )


def test_recommendation_engine_rank_and_dedupe():
    engine = BundleRecommendationEngine()
    metrics = build_metrics("bundle_rec")
    risk = build_risk("bundle_rec")

    output = engine.from_risk_assessment(risk, metrics)

    assert len(output) == 2
    assert output[0].priority.value == "urgent"
    assert output[1].priority.value in {"high", "medium"}
    assert output[0].action_type.value in {"outreach", "monitor"}
