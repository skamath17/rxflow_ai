"""
Tests for Bundle Risk Scoring Engine
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import Mock

from src.models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState
from src.models.metrics import BundleMetrics
from src.models.risk import (
    BundleBreakRisk, RefillAbandonmentRisk, RiskAssessmentSummary, RiskQuery, RiskList,
    RiskType, RiskSeverity, RiskDriverType, RiskDriver, RiskRecommendation,
    RiskModelConfig
)
from src.risk.risk_scoring_engine import BundleRiskScoringEngine
from src.utils.audit import AuditLogger


class TestBundleRiskScoringEngine:
    """Test cases for bundle risk scoring engine"""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing"""
        return AuditLogger()
    
    @pytest.fixture
    def risk_engine(self, audit_logger):
        """Create risk scoring engine for testing"""
        return BundleRiskScoringEngine(audit_logger=audit_logger)
    
    @pytest.fixture
    def sample_utc_datetime(self):
        """Sample UTC datetime for testing"""
        return datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    @pytest.fixture
    def sample_metrics(self, sample_utc_datetime):
        """Sample bundle metrics for testing"""
        return BundleMetrics(
            snapshot_id="snap_test_1234567890abcdef",
            member_id="mem_test_1234567890abcdef",
            refill_id="ref_test_1234567890abcdef",
            computed_timestamp=sample_utc_datetime,
            metrics_version="1.0",
            age_in_stage=Mock(),
            timing_overlap=Mock(),
            refill_gap=Mock(),
            bundle_alignment=Mock(),
            overall_risk_score=0.45,
            risk_severity=RiskSeverity.MEDIUM,
            primary_risk_factors=["timing_misalignment"],
            requires_attention=False,
            recommended_actions=["Review timing"],
            computation_time_ms=50
        )
    
    @pytest.fixture
    def high_risk_metrics(self, sample_utc_datetime):
        """High risk bundle metrics for testing"""
        metrics = BundleMetrics(
            snapshot_id="snap_high_risk",
            member_id="mem_high_risk",
            refill_id="ref_high_risk",
            computed_timestamp=sample_utc_datetime,
            metrics_version="1.0",
            age_in_stage=Mock(
                current_stage="pa_pending",
                days_in_current_stage=15,
                is_aging_in_stage=True,
                stage_age_percentile=1.0
            ),
            timing_overlap=Mock(
                bundle_size=3,
                refill_overlap_score=0.3,
                timing_variance_days=15.0,
                max_timing_gap_days=21,
                is_well_aligned=False,
                alignment_efficiency=0.4,
                fragmentation_risk=0.8,
                shipment_split_probability=0.7
            ),
            refill_gap=Mock(
                days_since_last_fill=120,
                days_until_next_due=-5,
                refill_gap_days=120,
                is_optimal_gap=False,
                gap_efficiency_score=0.0,
                abandonment_risk=0.8,
                urgency_score=1.0,
                days_supply_remaining=0,
                supply_buffer_days=-10
            ),
            bundle_alignment=Mock(
                bundle_id="bun_high_risk",
                bundle_member_count=3,
                bundle_refill_count=3,
                bundle_alignment_score=0.2,
                timing_alignment_score=0.2,
                bundle_efficiency_score=0.16,
                cost_savings_potential=0.0,
                split_risk_score=0.8,
                outreach_reduction_score=0.1,
                bundle_health_score=0.12
            ),
            overall_risk_score=0.85,
            risk_severity=RiskSeverity.HIGH,
            primary_risk_factors=["stage_aging", "bundle_fragmentation"],
            requires_attention=True,
            recommended_actions=["Expedite processing", "Review bundle composition"],
            computation_time_ms=75
        )
    
    @pytest.fixture
    def low_risk_metrics(self, sample_utc_datetime):
        """Low risk bundle metrics for testing"""
        metrics = BundleMetrics(
            snapshot_id="snap_low_risk",
            member_id="mem_low_risk",
            refill_id="ref_low_risk",
            computed_timestamp=sample_utc_datetime,
            metrics_version="1.0",
            age_in_stage=Mock(
                current_stage="completed",
                days_in_current_stage=0,
                is_aging_in_stage=False,
                stage_age_percentile=0.0
            ),
            timing_overlap=Mock(
                bundle_size=1,
                refill_overlap_score=1.0,
                timing_variance_days=0.0,
                max_timing_gap_days=0,
                is_well_aligned=True,
                alignment_efficiency=1.0,
                fragmentation_risk=0.0,
                shipment_split_probability=0.0
            ),
            refill_gap=Mock(
                days_since_last_fill=30,
                days_until_next_due=15,
                refill_gap_days=30,
                is_optimal_gap=True,
                gap_efficiency_score=0.9,
                abandonment_risk=0.1,
                urgency_score=0.2,
                days_supply_remaining=15,
                supply_buffer_days=5
            ),
            bundle_alignment=Mock(
                bundle_id="bun_low_risk",
                bundle_member_count=1,
                bundle_refill_count=1,
                bundle_alignment_score=0.95,
                timing_alignment_score=0.95,
                bundle_efficiency_score=0.85,
                cost_savings_potential=0.8,
                split_risk_score=0.1,
                outreach_reduction_score=0.7,
                bundle_health_score=0.9
            ),
            overall_risk_score=0.15,
            risk_severity=RiskSeverity.LOW,
            primary_risk_factors=[],
            requires_attention=False,
            recommended_actions=[],
            computation_time_ms=25
        )
    
    def test_assess_bundle_break_risk_high_risk(self, risk_engine, high_risk_metrics):
        """Test bundle break risk assessment for high risk scenario"""
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Verify basic structure
        assert risk.risk_id.startswith("bundle_break_")
        assert risk.bundle_id == "bun_high_risk"
        assert risk.assessment_timestamp is not None
        assert risk.model_version == "1.0"
        
        # Verify risk scores
        assert 0 <= risk.break_probability <= 1
        assert risk.break_severity == RiskSeverity.HIGH
        assert 0 <= risk.confidence_score <= 1
        
        # Verify drivers
        assert len(risk.primary_drivers) >= 1
        assert len(risk.secondary_drivers) >= 0
        assert all(isinstance(d, RiskDriver) for d in risk.primary_drivers)
        
        # Verify recommendations
        assert len(risk.recommendations) >= 1
        assert all(isinstance(r, RiskRecommendation) for r in risk.recommendations)
        
        # Verify performance metrics
        assert risk.computation_time_ms >= 0
    
    def test_assess_bundle_break_risk_low_risk(self, risk_engine, low_risk_metrics):
        """Test bundle break risk assessment for low risk scenario"""
        risk = risk_engine.assess_bundle_break_risk(low_risk_metrics)
        
        # Should be low risk
        assert risk.break_probability < 0.3
        assert risk.break_severity == RiskSeverity.LOW
        assert risk.requires_attention is False
        
        # Should have minimal recommendations
        assert len(risk.recommendations) <= 2
    
    def test_assess_abandonment_risk_high_risk(self, risk_engine, high_risk_metrics):
        """Test abandonment risk assessment for high risk scenario"""
        risk = risk_engine.assess_abandonment_risk(high_risk_metrics)
        
        # Verify basic structure
        assert risk.risk_id.startswith("abandonment_")
        assert risk.refill_id == "ref_high_risk"
        assert risk.member_id == "mem_high_risk"
        assert risk.assessment_timestamp is not None
        assert risk.model_version == "1.0"
        
        # Verify risk scores
        assert 0 <= risk.abandonment_probability <= 1
        assert risk.abandonment_severity == RiskSeverity.HIGH
        assert 0 <= risk.confidence_score <= 1
        
        # Verify drivers
        assert len(risk.primary_drivers) >= 1
        assert len(risk.secondary_drivers) >= 0
        assert all(isinstance(d, RiskDriver) for d in risk.primary_drivers)
        
        # Verify recommendations
        assert len(risk.recommendations) >= 1
        assert all(isinstance(r, RiskRecommendation) for r in risk.recommendations)
        
        # Verify performance metrics
        assert risk.computation_time_ms >= 0
    
    def test_assess_abandonment_risk_low_risk(self, risk_engine, low_risk_metrics):
        """Test abandonment risk assessment for low risk scenario"""
        risk = risk_engine.assess_abandonment_risk(low_risk_metrics)
        
        # Should be low risk
        assert risk.abandonment_probability < 0.3
        assert risk.abandonment_severity == RiskSeverity.LOW
        assert risk.requires_attention is False
        
        # Should have minimal recommendations
        assert len(risk.recommendations) <= 2
    
    def test_batch_risk_assessment(self, risk_engine, high_risk_metrics, low_risk_metrics):
        """Test batch risk assessment"""
        metrics_list = [high_risk_metrics, low_risk_metrics]
        
        risks = risk_engine.assess_batch_risks(metrics_list)
        
        # Should return assessments for both metrics
        assert len(risks) == 2
        
        # Should include both risk types
        bundle_risks = [r for r in risks if isinstance(r, BundleBreakRisk)]
        abandonment_risks = [r for r in risks if isinstance(r, RefillAbandonmentRisk)]
        
        assert len(bundle_risks) == 1
        assert len(abandonment_risks) == 1
        
        # Verify high risk assessment
        high_risk = bundle_risks[0]
        assert high_risk.break_probability > 0.6
        assert high_risk.break_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]
        
        # Verify low risk assessment
        low_risk = abandonment_risks[0]
        assert low_risk.abandonment_probability < 0.3
        assert low_risk.abandonment_severity == RiskSeverity.LOW
    
    def test_get_risk_assessment(self, risk_engine, high_risk_metrics):
        """Test retrieving risk assessment by ID"""
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Retrieve by ID
        retrieved = risk_engine.get_risk_assessment(risk.risk_id)
        
        # Should return identical assessment
        assert retrieved is not None
        assert retrieved.risk_id == risk.risk_id
        assert retrieved.break_probability == risk.break_probability
        assert retrieved.break_severity == risk.break_severity
    
    def test_get_nonexistent_risk_assessment(self, risk_engine):
        """Test retrieving non-existent risk assessment"""
        retrieved = risk_engine.get_risk_assessment("nonexistent")
        assert retrieved is None
    
    def test_query_risk_assessments_by_type(self, risk_engine, high_risk_metrics, low_risk_metrics):
        """Test querying risk assessments by type"""
        # Assess both types
        bundle_risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        abandonment_risk = risk_engine.assess_abandonment_risk(low_risk_metrics)
        
        # Query by bundle break type
        query = RiskQuery(risk_type=RiskType.BUNDLE_BREAK)
        results = risk_engine.query_risk_assessments(query)
        
        # Should return only bundle break risks
        assert len(results.risks) == 1
        assert isinstance(results.risks[0], BundleBreakRisk)
        assert results.total_count == 1
        
        # Query by abandonment type
        query = RiskQuery(risk_type=RiskType.REFILL_ABANDONMENT)
        results = risk_engine.query_risk_assessments(query)
        
        # Should return only abandonment risks
        assert len(results.risks) == 1
        assert isinstance(results.risks[0], RefillAbandonmentRisk)
        assert results.total_count == 1
    
    def test_query_risk_assessments_by_severity(self, risk_engine, high_risk_metrics, low_risk_metrics):
        """Test querying risk assessments by severity"""
        # Assess both risk levels
        high_risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        low_risk = risk_engine.assess_abandonment_risk(low_risk_metrics)
        
        # Query by high severity
        query = RiskQuery(severity=RiskSeverity.HIGH)
        results = risk_engine.query_risk_assessments(query)
        
        # Should return high risk assessments
        assert len(results.risks) >= 1
        for risk in results.risks:
            assert risk.break_severity == RiskSeverity.HIGH or risk.abandonment_severity == RiskSeverity.HIGH
        
        # Query by low severity
        query = RiskQuery(severity=RiskSeverity.LOW)
        results = risk_engine.query_risk_assessments(query)
        
        # Should return low risk assessments
        assert len(results.risks) >= 1
        for risk in results.risks:
            assert risk.break_severity == RiskSeverity.LOW or risk.abandonment_severity == RiskSeverity.LOW
    
    def test_query_risk_assessments_pagination(self, risk_engine, high_risk_metrics, low_risk_metrics):
        """Test risk assessment query pagination"""
        # Create multiple risk assessments
        risks = []
        for i in range(5):
            metrics = high_risk_metrics.copy(deep=True)
            metrics.snapshot_id = f"snap_high_risk_{i}"
            metrics.member_id = f"mem_high_risk_{i}"
            metrics.refill_id = f"ref_high_risk_{i}"
            risks.append(risk_engine.assess_bundle_break_risk(metrics))
        
        # Query with pagination
        query = RiskQuery(limit=2, offset=0)
        results1 = risk_engine.query_risk_assessments(query)
        
        # Second page
        query2 = RiskQuery(limit=2, offset=2)
        results2 = risk_engine.query_risk_assessments(query2)
        
        # Verify pagination
        assert len(results1.risks) == 2
        assert len(results2.risks) == 2
        assert results1.has_more is True
        assert results2.has_more is True
        
        # Third page
        query3 = RiskQuery(limit=2, offset=4)
        results3 = risk_engine.query_risk_assessments(query3)
        
        assert len(results3.risks) == 1
        assert results3.has_more is False
    
    def test_get_bundle_risks(self, risk_engine, high_risk_metrics):
        """Test getting all risk assessments for a bundle"""
        # Assess bundle break risk
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Get risks for bundle
        bundle_risks = risk_engine.get_bundle_risks("bun_high_risk")
        
        # Should return the assessed risk
        assert len(bundle_risks) == 1
        assert bundle_risks[0].risk_id == risk.risk_id
        assert bundle_risks[0].bundle_id == "bun_high_risk"
    
    def test_get_member_risks(self, risk_engine, high_risk_metrics):
        """Test getting all risk assessments for a member"""
        # Assess abandonment risk
        risk = risk_engine.assess_abandonment_risk(high_risk_metrics)
        
        # Get risks for member
        member_risks = risk_engine.get_member_risks("mem_high_risk")
        
        # Should return the assessed risk
        assert len(member_risks) == 1
        assert member_risks[0].risk_id == risk.risk_id
        assert member_risks[0].member_id == "mem_high_risk"
    
    def test_risk_assessment_summary_generation(self, risk_engine, high_risk_metrics, low_risk_metrics):
        """Test risk assessment summary generation"""
        # Assess multiple risks
        bundle_risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        abandonment_risk = risk_engine.assessment_abandonment_risk(low_risk_metrics)
        
        # Query with summary
        query = RiskQuery(limit=10)
        results = risk_engine.query_risk_assessments(query)
        
        # Should have summary
        assert results.summary is not None
        assert isinstance(results.summary, RiskAssessmentSummary)
        
        # Verify summary statistics
        assert results.summary.total_assessments == 2
        assert 0 <= results.summary.avg_break_probability <= 1
        assert 0 <= results.summary.avg_abandonment_probability <= 1
        assert results.summary.high_risk_count >= 1
        assert results.summary.assessment_time_ms >= 0
    
    def test_risk_driver_identification(self, risk_engine, high_risk_metrics):
        """Test risk driver identification"""
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Should have primary drivers
        assert len(risk.primary_drivers) >= 1
        assert len(risk.secondary_drivers) >= 0
        
        # Verify driver structure
        for driver in risk.primary_drivers:
            assert isinstance(driver, RiskDriver)
            assert 0 <= driver.impact_score <= 1
            assert 0 <= driver.confidence <= 1
            assert driver.driver_type in [d.value for d in RiskDriverType]
            assert driver.driver_name is not None
            assert driver.evidence is not None
            assert driver.metric_values is not None
    
    def test_recommendation_generation(self, risk_engine, high_risk_metrics):
        """Test recommendation generation"""
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Should have recommendations for high risk
        assert len(risk.recommendations) >= 1
        
        # Verify recommendation structure
        for rec in risk.recommendations:
            assert isinstance(rec, RiskRecommendation)
            assert rec.recommendation_id is not None
            assert rec.priority in ["urgent", "high", "medium", "low"]
            assert rec.category is not None
            assert rec.title is not None
            assert rec.description is not None
            assert len(rec.action_steps) >= 0
            assert rec.expected_impact is not None
            assert rec.time_to_implement is not None
            assert rec.applicable_stages is not None
            assert rec.required_resources is not None
    
    def test_risk_severity_determination(self, risk_engine):
        """Test risk severity determination"""
        # Test low probability
        assert risk_engine._determine_risk_severity(0.2, risk_engine.break_thresholds) == RiskSeverity.LOW
        assert risk_engine._determine_risk_severity(0.4, risk_engine.break_thresholds) == RiskSeverity.MEDIUM
        assert risk_engine._determine_risk_severity(0.7, risk_engine.break_thresholds) == RiskSeverity.HIGH
        assert risk_engine._determine_risk_severity(0.9, risk_engine.break_thresholds) == RiskSeverity.CRITICAL
        
        # Test abandonment thresholds
        assert risk_engine._determine_risk_severity(0.2, risk_engine.abandonment_thresholds) == RiskSeverity.LOW
        assert risk_engine._determine_risk_severity(0.5, risk_engine.abandonment_thresholds) == RiskSeverity.MEDIUM
        assert risk_engine._determine_risk_severity(0.8, risk_engine.abandonment_thresholds) == RiskSeverity.HIGH
        assert risk_engine._determine_risk_severity(0.95, risk_engine.abandonment_thresholds) == RiskSeverity.CRITICAL
    
    def test_confidence_computation(self, risk_engine, sample_metrics):
        """Test confidence score computation"""
        # Test with no drivers (low confidence)
        risk = risk_engine.assess_bundle_break_risk(sample_metrics)
        assert risk.confidence_score < 0.7
        
        # Test with strong drivers (high confidence)
        # Mock drivers with high confidence
        sample_metrics.primary_drivers = [
            RiskDriver(
                driver_type=RiskDriverType.TIMING_MISALIGNMENT,
                driver_name="Test Driver",
                impact_score=0.8,
                confidence=0.9,
                evidence={},
                metric_values={}
            )
        ]
        risk = risk_engine.assess_bundle_break_risk(sample_metrics)
        assert risk.confidence_score >= 0.8
    
    def test_audit_logging(self, risk_engine, high_risk_metrics):
        """Test audit logging during risk assessment"""
        initial_count = len(risk_engine.audit_logger._audit_trail)
        
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Should have logged risk assessment
        assert len(risk_engine.audit_logger._audit_trail) > initial_count
        
        # Find the risk assessment log
        risk_logs = risk_engine.audit_logger.get_audit_trail(action="risk_assessment")
        assert len(risk_logs) >= 1
        
        log = risk_logs[-1]
        assert log.risk_id == risk.risk_id
        assert log.details["probability"] == risk.break_probability
        assert log.details["severity"] == risk.break_severity.value
        assert log.processing_time_ms is not None
    
    def test_performance_metrics(self, risk_engine, sample_metrics):
        """Test performance metrics computation"""
        import time
        
        # Measure assessment time
        start_time = time.time()
        risk = risk_engine.assess_bundle_break_risk(sample_metrics)
        end_time = time.time()
        
        # Should complete quickly
        assessment_time = (end_time - start_time) * 1000
        assert assessment_time < 100  # Less than 100ms
        
        # Should track computation time
        assert risk.computation_time_ms >= 0
    
    def test_data_quality_assessment(self, risk_engine, sample_metrics):
        """Test data quality assessment for confidence calculation"""
        # Test complete metrics (high quality)
        risk = risk_engine.assess_bundle_break_risk(sample_metrics)
        assert risk.confidence_score >= 0.8
        
        # Test incomplete metrics (lower quality)
        incomplete_metrics = BundleMetrics(
            snapshot_id="snap_incomplete",
            member_id="mem_incomplete",
            refill_id="ref_incomplete",
            computed_timestamp=datetime.now(timezone.utc),
            metrics_version="1.0",
            age_in_stage=Mock(
                current_stage="unknown",
                days_in_current_stage=0,
                is_aging_in_stage=False,
                stage_age_percentile=0.0
            ),
            timing_overlap=Mock(
                bundle_size=0,
                refill_overlap_score=0.0,
                timing_variance_days=0.0,
                max_timing_gap_days=0,
                is_well_aligned=False,
                alignment_efficiency=0.0,
                fragmentation_risk=0.0,
                shipment_split_probability=0.0
            ),
            refill_gap=Mock(
                days_since_last_fill=0,
                days_until_next_due=0,
                refill_gap_days=0,
                is_optimal_gap=False,
                gap_efficiency_score=0.0,
                abandonment_risk=0.0,
                urgency_score=0.0,
                days_supply_remaining=None,
                supply_buffer_days=None
            ),
            bundle_alignment=Mock(
                bundle_id=None,
                bundle_member_count=0,
                bundle_refill_count=0,
                bundle_alignment_score=None,
                timing_alignment_score=None,
                bundle_efficiency_score=None,
                cost_savings_potential=None,
                split_risk_score=None,
                outreach_reduction_score=None,
                bundle_health_score=None
            ),
            overall_risk_score=0.0,
            risk_severity=RiskSeverity.LOW,
            primary_risk_factors=[],
            requires_attention=False,
            recommended_actions=[],
            computation_time_ms=0
        )
        
        risk = risk_engine.assess_bundle_break_risk(incomplete_metrics)
        assert risk.confidence_score < 0.7
    
    def test_estimated_timeframe_estimation(self, risk_engine, high_risk_metrics):
        """Test timeframe estimation for risk events"""
        risk = risk_engine.estimate_break_timeframe(high_risk_metrics, [])
        
        # Should provide timeframe for aging refills
        assert risk is not None
        assert risk in ["2-4 weeks", "1-2 weeks", "1 week", "3-7 days"]
        
        # Test with different aging levels
        aging_metrics = BundleMetrics(
            snapshot_id="snap_aging",
            member_id="mem_aging",
            refill_id="ref_aging",
            computed_timestamp=datetime.now(timezone.utc),
            age_in_stage=Mock(
                current_stage="pa_pending",
                days_in_current_stage=5
            ),
            timing_overlap=Mock(),
            refill_gap=Mock(),
            bundle_alignment=Mock()
        )
        
        timeframe = risk_engine._estimate_break_timeframe(aging_metrics, [])
        assert timeframe in ["1 week", "3-7 days"]
    
    def test_critical_factors_identification(self, risk_engine, high_risk_metrics):
        """Test critical factors identification"""
        risk = risk_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Should identify critical factors from drivers
        critical_factors = risk_engine._identify_critical_factors(risk.primary_drivers)
        assert len(critical_factors) >= 1
        assert all(isinstance(factor, str) for factor in critical_factors)
        
        # Test with timing misalignment driver
        timing_driver = RiskDriver(
            driver_type=RiskDriverType.TIMING_MISALIGNMENT,
            driver_name="Bundle Timing Misalignment",
            impact_score=0.8,
            confidence=0.9,
            evidence={
                "timing_alignment_score": 0.3,
                "max_timing_gap": 21
            }
        )
        factors = risk_engine._identify_critical_factors([timing_driver])
        assert "Timing alignment score" in factors
        assert "Maximum timing gap" in factors
    
    def test_model_configuration(self):
        """Test risk model configuration"""
        config = RiskModelConfig(
            model_name="test_model",
            model_version="1.0",
            break_risk_thresholds={
                "low": 0.25,
                "medium": 0.5,
                "high": 0.75
            },
            driver_weights={
                "timing_misalignment": 0.4,
                "bundle_fragmentation": 0.3,
                "stage_aging": 0.2,
                "pa_processing_delay": 0.1
            }
        )
        
        # Validate thresholds
        assert config.break_risk_thresholds["low"] == 0.25
        assert config.break_risk_thresholds["medium"] == 0.5
        assert config.break_risk_thresholds["high"] == 0.75
        
        # Validate weights sum to 1.0
        total_weight = sum(config.driver_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small rounding errors
        
        # Validate confidence threshold
        assert config.min_confidence_threshold == 0.7
    
    def test_engine_with_custom_config(self, high_risk_metrics):
        """Test engine with custom configuration"""
        custom_config = RiskModelConfig(
            model_name="custom_model",
            break_risk_thresholds={
                "low": 0.2,
                "medium": 0.5,
                "high": 0.8
            }
        )
        
        custom_engine = BundleRiskScoringEngine(config=custom_config)
        risk = custom_engine.assess_bundle_break_risk(high_risk_metrics)
        
        # Should use custom thresholds
        assert custom_engine.break_thresholds["low"] == 0.2
        assert custom_engine.break_thresholds["high"] == 0.8
        
        # Should adjust severity based on custom thresholds
        # (0.75 is high risk with custom config vs 0.8 with default)
        assert risk.break_severity == RiskSeverity.HIGH
