"""
Basic Tests for Bundle Risk Scoring Engine
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

from src.models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState
from src.models.metrics import BundleMetrics, AgeInStageMetrics, TimingOverlapMetrics, RefillGapMetrics, BundleAlignmentMetrics
from src.models.risk import (
    BundleBreakRisk, RefillAbandonmentRisk, RiskAssessmentSummary, RiskQuery, RiskList,
    RiskType, RiskSeverity, RiskDriverType, RiskDriver, RiskRecommendation,
    RiskModelConfig
)
from src.risk.risk_scoring_engine import BundleRiskScoringEngine
from src.utils.audit import AuditLogger


class TestBundleRiskScoringEngineBasic:
    """Basic test cases for bundle risk scoring engine"""
    
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
    def high_risk_metrics(self, sample_utc_datetime):
        """High risk bundle metrics for testing"""
        return BundleMetrics(
            snapshot_id="snap_high_risk",
            member_id="mem_high_risk",
            refill_id="ref_high_risk",
            computed_timestamp=sample_utc_datetime,
            metrics_version="1.0",
            age_in_stage=AgeInStageMetrics(
                current_stage="pa_pending",
                days_in_current_stage=15,
                stage_history={},
                initiation_to_eligible_days=2,
                eligibility_to_bundled_days=0,
                bundled_to_shipped_days=None,
                is_aging_in_stage=True,
                stage_age_percentile=1.0
            ),
            timing_overlap=TimingOverlapMetrics(
                bundle_id="bun_high_risk",
                bundle_size=3,
                refill_overlap_score=0.3,
                timing_variance_days=15.0,
                max_timing_gap_days=21,
                is_well_aligned=False,
                alignment_efficiency=0.4,
                fragmentation_risk=0.8,
                shipment_split_probability=0.7
            ),
            refill_gap=RefillGapMetrics(
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
            bundle_alignment=BundleAlignmentMetrics(
                bundle_id="bun_high_risk",
                bundle_member_count=3,
                bundle_refill_count=3,
                bundle_alignment_score=0.2,
                timing_alignment_score=0.2,
                bundle_efficiency_score=0.16,
                cost_savings_potential=0.0,
                split_risk_score=0.8,
                outreach_reduction_score=0.1,
                bundle_health_score=0.12,
                recommended_actions=["Review bundle composition"]
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
        return BundleMetrics(
            snapshot_id="snap_low_risk",
            member_id="mem_low_risk",
            refill_id="ref_low_risk",
            computed_timestamp=sample_utc_datetime,
            metrics_version="1.0",
            age_in_stage=AgeInStageMetrics(
                current_stage="completed",
                days_in_current_stage=0,
                stage_history={},
                initiation_to_eligible_days=0,
                eligibility_to_bundled_days=0,
                bundled_to_shipped_days=0,
                is_aging_in_stage=False,
                stage_age_percentile=0.0
            ),
            timing_overlap=TimingOverlapMetrics(
                bundle_id="bun_low_risk",
                bundle_size=1,
                refill_overlap_score=1.0,
                timing_variance_days=0.0,
                max_timing_gap_days=0,
                is_well_aligned=True,
                alignment_efficiency=1.0,
                fragmentation_risk=0.0,
                shipment_split_probability=0.0
            ),
            refill_gap=RefillGapMetrics(
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
            bundle_alignment=BundleAlignmentMetrics(
                bundle_id="bun_low_risk",
                bundle_member_count=1,
                bundle_refill_count=1,
                bundle_alignment_score=0.95,
                timing_alignment_score=0.95,
                bundle_efficiency_score=0.85,
                cost_savings_potential=0.8,
                split_risk_score=0.1,
                outreach_reduction_score=0.7,
                bundle_health_score=0.9,
                recommended_actions=[]
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
        assert risk.assessment_timestamp is not None
    
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
        assert risk.assessment_timestamp is not None
    
    def test_assess_abandonment_risk_low_risk(self, risk_engine, low_risk_metrics):
        """Test abandonment risk assessment for low risk scenario"""
        risk = risk_engine.assess_abandonment_risk(low_risk_metrics)
        
        # Should be low risk
        assert risk.abandonment_probability < 0.3
        assert risk.abandonment_severity == RiskSeverity.LOW
        assert risk.requires_attention is False
        
        # Should have minimal recommendations
        assert len(risk.recommendations) <= 2
    
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
    
    def test_performance_metrics(self, risk_engine, low_risk_metrics):
        """Test performance metrics computation"""
        import time
        
        # Measure assessment time
        start_time = time.time()
        risk = risk_engine.assess_bundle_break_risk(low_risk_metrics)
        end_time = time.time()
        
        # Should complete quickly
        assessment_time = (end_time - start_time) * 1000
        assert assessment_time < 100  # Less than 100ms
        
        # Should track assessment timestamp
        assert risk.assessment_timestamp is not None
    
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
