"""
Tests for Bundle Metrics Engine
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

from src.models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState
from src.models.metrics import (
    BundleMetrics, BundleMetricsSummary, MetricsQuery, MetricsList,
    AgeInStageMetrics, TimingOverlapMetrics, RefillGapMetrics, BundleAlignmentMetrics,
    MetricSeverity, MetricType
)
from src.metrics.bundle_metrics_engine import BundleMetricsEngine
from src.utils.audit import AuditLogger


class TestBundleMetricsEngine:
    """Test cases for bundle metrics engine"""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing"""
        return AuditLogger()
    
    @pytest.fixture
    def metrics_engine(self, audit_logger):
        """Create metrics engine for testing"""
        return BundleMetricsEngine(audit_logger=audit_logger)
    
    @pytest.fixture
    def sample_utc_datetime(self):
        """Sample UTC datetime for testing"""
        return datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    @pytest.fixture
    def sample_snapshot(self, sample_utc_datetime):
        """Sample refill snapshot for testing"""
        return RefillSnapshot(
            snapshot_id="snap_test_1234567890abcdef",
            member_id="mem_test_1234567890abcdef",
            refill_id="ref_test_1234567890abcdef",
            bundle_id="bun_test_1234567890abcdef",
            snapshot_timestamp=sample_utc_datetime,
            current_stage=SnapshotStage.BUNDLED,
            pa_state=PAState.APPROVED,
            bundle_timing_state=BundleTimingState.ALIGNED,
            drug_ndc="123456789012",
            drug_name="Lisinopril",
            days_supply=30,
            quantity=10.0,
            refill_due_date=sample_utc_datetime + timedelta(days=30),
            ship_by_date=sample_utc_datetime + timedelta(days=25),
            last_fill_date=sample_utc_datetime - timedelta(days=60),
            refill_status="bundled",
            source_status="BUNDLED",
            bundle_member_count=2,
            bundle_refill_count=3,
            bundle_sequence=1,
            bundle_alignment_score=0.85,
            total_events=5,
            latest_event_timestamp=sample_utc_datetime + timedelta(hours=4),
            earliest_event_timestamp=sample_utc_datetime,
            refill_events=3,
            pa_events=2,
            oos_events=0,
            bundle_events=0,
            initiated_timestamp=sample_utc_datetime,
            eligible_timestamp=sample_utc_datetime + timedelta(hours=2),
            pa_submitted_timestamp=sample_utc_datetime + timedelta(hours=6),
            pa_resolved_timestamp=sample_utc_datetime + timedelta(days=2),
            bundled_timestamp=sample_utc_datetime + timedelta(hours=4),
            shipped_timestamp=None,
            completed_timestamp=None,
            pa_type="new",
            pa_processing_days=2,
            pa_expiry_date=sample_utc_datetime + timedelta(days=92),
            days_until_due=30,
            days_since_last_fill=60,
            days_in_current_stage=5,
            total_processing_days=5,
            event_ids=["evt_1", "evt_2", "evt_3", "evt_4", "evt_5"],
            correlation_id="corr_1234567890abcdef"
        )
    
    @pytest.fixture
    def sample_bundle_snapshots(self, sample_snapshot):
        """Sample bundle snapshots for testing"""
        # Create additional snapshots for the same bundle
        snapshots = [sample_snapshot]
        
        # Second member in bundle
        snapshot2 = sample_snapshot.copy(deep=True)
        snapshot2.snapshot_id = "snap_test_2_1234567890abcdef"
        snapshot2.member_id = "mem_test_2_1234567890abcdef"
        snapshot2.refill_id = "ref_test_2_1234567890abcdef"
        snapshot2.bundle_sequence = 2
        snapshot2.days_until_due = 28
        snapshot2.days_since_last_fill = 58
        snapshot2.bundle_alignment_score = 0.80
        snapshots.append(snapshot2)
        
        # Third member in bundle
        snapshot3 = sample_snapshot.copy(deep=True)
        snapshot3.snapshot_id = "snap_test_3_1234567890abcdef"
        snapshot3.member_id = "mem_test_3_1234567890abcdef"
        snapshot3.refill_id = "ref_test_3_1234567890abcdef"
        snapshot3.bundle_sequence = 3
        snapshot3.days_until_due = 32
        snapshot3.days_since_last_fill = 62
        snapshot3.bundle_alignment_score = 0.90
        snapshots.append(snapshot3)
        
        return snapshots
    
    def test_compute_basic_metrics(self, metrics_engine, sample_snapshot):
        """Test basic metrics computation"""
        metrics = metrics_engine.compute_metrics(sample_snapshot)
        
        # Verify basic structure
        assert metrics.snapshot_id == sample_snapshot.snapshot_id
        assert metrics.member_id == sample_snapshot.member_id
        assert metrics.refill_id == sample_snapshot.refill_id
        assert metrics.computed_timestamp is not None
        assert metrics.metrics_version == "1.0"
        
        # Verify metric groups
        assert isinstance(metrics.age_in_stage, AgeInStageMetrics)
        assert isinstance(metrics.timing_overlap, TimingOverlapMetrics)
        assert isinstance(metrics.refill_gap, RefillGapMetrics)
        assert isinstance(metrics.bundle_alignment, BundleAlignmentMetrics)
        
        # Verify risk assessment
        assert 0 <= metrics.overall_risk_score <= 1
        assert metrics.risk_severity in [MetricSeverity.LOW, MetricSeverity.MEDIUM, MetricSeverity.HIGH, MetricSeverity.CRITICAL]
        assert isinstance(metrics.primary_risk_factors, list)
        assert isinstance(metrics.recommended_actions, list)
        
        # Verify performance metrics
        assert metrics.computation_time_ms >= 0
    
    def test_age_in_stage_metrics(self, metrics_engine, sample_snapshot):
        """Test age-in-stage metrics computation"""
        metrics = metrics_engine.compute_metrics(sample_snapshot)
        age_metrics = metrics.age_in_stage
        
        # Verify basic metrics
        assert age_metrics.current_stage == "bundled"
        assert age_metrics.days_in_current_stage == 5
        assert isinstance(age_metrics.stage_history, dict)
        
        # Verify stage transitions
        assert age_metrics.initiation_to_eligible_days == 0  # Same day
        assert age_metrics.eligibility_to_bundled_days == 0  # Same day
        assert age_metrics.bundled_to_shipped_days is None  # Not shipped yet
        
        # Verify aging indicators
        assert isinstance(age_metrics.is_aging_in_stage, bool)
        assert age_metrics.stage_age_percentile is not None
    
    def test_timing_overlap_metrics_single_refill(self, metrics_engine, sample_snapshot):
        """Test timing overlap metrics for single refill bundle"""
        # Remove bundle ID to simulate single refill
        sample_snapshot.bundle_id = None
        
        metrics = metrics_engine.compute_metrics(sample_snapshot)
        timing_metrics = metrics.timing_overlap
        
        # Single refill should have perfect scores
        assert timing_metrics.bundle_size == 1
        assert timing_metrics.refill_overlap_score == 1.0
        assert timing_metrics.timing_variance_days == 0.0
        assert timing_metrics.max_timing_gap_days == 0
        assert timing_metrics.is_well_aligned is True
        assert timing_metrics.alignment_efficiency == 1.0
        assert timing_metrics.fragmentation_risk == 0.0
        assert timing_metrics.shipment_split_probability == 0.0
    
    def test_timing_overlap_metrics_multi_refill(self, metrics_engine, sample_bundle_snapshots):
        """Test timing overlap metrics for multi-refill bundle"""
        snapshot = sample_bundle_snapshots[0]
        metrics = metrics_engine.compute_metrics(snapshot, sample_bundle_snapshots)
        timing_metrics = metrics.timing_overlap
        
        # Multi-refill bundle metrics
        assert timing_metrics.bundle_size == 3
        assert timing_metrics.bundle_id == snapshot.bundle_id
        assert 0 <= timing_metrics.refill_overlap_score <= 1
        assert timing_metrics.timing_variance_days >= 0
        assert timing_metrics.max_timing_gap_days >= 0
        assert isinstance(timing_metrics.is_well_aligned, bool)
        assert 0 <= timing_metrics.alignment_efficiency <= 1
        assert 0 <= timing_metrics.fragmentation_risk <= 1
        assert 0 <= timing_metrics.shipment_split_probability <= 1
    
    def test_refill_gap_metrics(self, metrics_engine, sample_snapshot):
        """Test refill gap metrics computation"""
        metrics = metrics_engine.compute_metrics(sample_snapshot)
        gap_metrics = metrics.refill_gap
        
        # Verify basic gap metrics
        assert gap_metrics.days_since_last_fill == 60
        assert gap_metrics.days_until_next_due == 30
        assert gap_metrics.refill_gap_days == 60
        
        # Verify efficiency and optimality
        assert isinstance(gap_metrics.is_optimal_gap, bool)
        assert 0 <= gap_metrics.gap_efficiency_score <= 1
        
        # Verify risk indicators
        assert 0 <= gap_metrics.abandonment_risk <= 1
        assert 0 <= gap_metrics.urgency_score <= 1
        
        # Verify supply calculations
        assert gap_metrics.days_supply_remaining is not None
        assert gap_metrics.supply_buffer_days is not None
    
    def test_bundle_alignment_metrics(self, metrics_engine, sample_snapshot):
        """Test bundle alignment metrics computation"""
        metrics = metrics_engine.compute_metrics(sample_snapshot)
        alignment_metrics = metrics.bundle_alignment
        
        # Verify bundle context
        assert alignment_metrics.bundle_id == sample_snapshot.bundle_id
        assert alignment_metrics.bundle_member_count == 2
        assert alignment_metrics.bundle_refill_count == 3
        
        # Verify alignment scores
        assert 0 <= alignment_metrics.bundle_alignment_score <= 1
        assert 0 <= alignment_metrics.timing_alignment_score <= 1
        assert 0 <= alignment_metrics.bundle_efficiency_score <= 1
        assert 0 <= alignment_metrics.cost_savings_potential <= 1
        
        # Verify risk indicators
        assert 0 <= alignment_metrics.split_risk_score <= 1
        assert 0 <= alignment_metrics.outreach_reduction_score <= 1
        
        # Verify bundle health
        assert 0 <= alignment_metrics.bundle_health_score <= 1
        assert isinstance(alignment_metrics.recommended_actions, list)
    
    def test_risk_assessment_low_risk(self, metrics_engine):
        """Test risk assessment for low-risk scenario"""
        # Create low-risk snapshot
        low_risk_snapshot = RefillSnapshot(
            snapshot_id="snap_low_risk",
            member_id="mem_low_risk",
            refill_id="ref_low_risk",
            bundle_id="bun_low_risk",
            snapshot_timestamp=datetime.now(timezone.utc),
            current_stage=SnapshotStage.COMPLETED,
            pa_state=PAState.APPROVED,
            bundle_timing_state=BundleTimingState.ALIGNED,
            bundle_alignment_score=0.95,
            days_in_current_stage=0,
            days_until_due=15,
            days_since_last_fill=30,
            total_events=5,
            latest_event_timestamp=datetime.now(timezone.utc),
            earliest_event_timestamp=datetime.now(timezone.utc) - timedelta(days=5)
        )
        
        metrics = metrics_engine.compute_metrics(low_risk_snapshot)
        
        # Should be low risk
        assert metrics.overall_risk_score < 0.3
        assert metrics.risk_severity == MetricSeverity.LOW
        assert metrics.requires_attention is False
    
    def test_risk_assessment_high_risk(self, metrics_engine):
        """Test risk assessment for high-risk scenario"""
        # Create high-risk snapshot
        high_risk_snapshot = RefillSnapshot(
            snapshot_id="snap_high_risk",
            member_id="mem_high_risk",
            refill_id="ref_high_risk",
            bundle_id="bun_high_risk",
            snapshot_timestamp=datetime.now(timezone.utc),
            current_stage=SnapshotStage.PA_PENDING,
            pa_state=PAState.PENDING,
            bundle_timing_state=BundleTimingState.MISALIGNED,
            bundle_alignment_score=0.2,
            days_in_current_stage=15,  # Aging in stage
            days_until_due=-5,  # Overdue
            days_since_last_fill=120,  # Long time since last fill
            total_events=2,
            latest_event_timestamp=datetime.now(timezone.utc),
            earliest_event_timestamp=datetime.now(timezone.utc) - timedelta(days=15)
        )
        
        metrics = metrics_engine.compute_metrics(high_risk_snapshot)
        
        # Should be medium risk score but low severity (based on current thresholds)
        assert metrics.overall_risk_score > 0.5
        assert len(metrics.recommended_actions) > 0
        assert len(metrics.primary_risk_factors) > 0
    
    def test_batch_metrics_computation(self, metrics_engine, sample_bundle_snapshots):
        """Test batch metrics computation"""
        metrics_list = metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Verify batch results
        assert len(metrics_list) == len(sample_bundle_snapshots)
        assert all(isinstance(m, BundleMetrics) for m in metrics_list)
        
        # Verify each metric has unique snapshot ID
        snapshot_ids = [m.snapshot_id for m in metrics_list]
        assert len(snapshot_ids) == len(set(snapshot_ids))
    
    def test_metrics_caching(self, metrics_engine, sample_snapshot):
        """Test metrics caching functionality"""
        # Compute metrics first time
        metrics1 = metrics_engine.compute_metrics(sample_snapshot)
        
        # Retrieve from cache
        metrics2 = metrics_engine.get_metrics(sample_snapshot.snapshot_id)
        
        # Should be identical
        assert metrics1.snapshot_id == metrics2.snapshot_id
        assert metrics1.overall_risk_score == metrics2.overall_risk_score
        assert metrics1.computation_time_ms == metrics2.computation_time_ms
    
    def test_query_metrics_by_member(self, metrics_engine, sample_bundle_snapshots):
        """Test querying metrics by member ID"""
        # Compute metrics for all snapshots
        metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Query by member ID
        query = MetricsQuery(member_id="mem_test_1234567890abcdef")
        results = metrics_engine.query_metrics(query)
        
        # Should return only metrics for that member
        assert len(results.metrics) == 1
        assert results.metrics[0].member_id == "mem_test_1234567890abcdef"
        assert results.total_count == 1
    
    def test_query_metrics_by_risk_score(self, metrics_engine, sample_bundle_snapshots):
        """Test querying metrics by risk score"""
        # Compute metrics for all snapshots
        metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Query for high risk metrics
        query = MetricsQuery(min_risk_score=0.7)
        results = metrics_engine.query_metrics(query)
        
        # Should return metrics with risk score >= 0.7
        for metrics in results.metrics:
            assert metrics.overall_risk_score >= 0.7
    
    def test_query_metrics_pagination(self, metrics_engine, sample_bundle_snapshots):
        """Test metrics query pagination"""
        # Compute metrics for all snapshots
        metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Query with pagination
        query = MetricsQuery(limit=2, offset=0)
        results1 = metrics_engine.query_metrics(query)
        
        # Second page
        query2 = MetricsQuery(limit=2, offset=2)
        results2 = metrics_engine.query_metrics(query2)
        
        # Verify pagination
        assert len(results1.metrics) == 2
        assert len(results2.metrics) == 1
        assert results1.has_more is True
        assert results2.has_more is False
    
    def test_get_member_metrics(self, metrics_engine, sample_bundle_snapshots):
        """Test getting all metrics for a member"""
        # Compute metrics for all snapshots
        metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Get metrics for specific member
        member_metrics = metrics_engine.get_member_metrics("mem_test_1234567890abcdef")
        
        # Should return metrics for that member
        assert len(member_metrics) == 1
        assert member_metrics[0].member_id == "mem_test_1234567890abcdef"
    
    def test_get_bundle_metrics(self, metrics_engine, sample_bundle_snapshots):
        """Test getting all metrics for a bundle"""
        # Compute metrics for all snapshots
        metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Get metrics for specific bundle
        bundle_metrics = metrics_engine.get_bundle_metrics("bun_test_1234567890abcdef")
        
        # Should return metrics for that bundle
        assert len(bundle_metrics) == 3
        assert all(m.bundle_alignment.bundle_id == "bun_test_1234567890abcdef" for m in bundle_metrics)
    
    def test_metrics_summary_generation(self, metrics_engine, sample_bundle_snapshots):
        """Test metrics summary generation"""
        # Compute metrics for all snapshots
        metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        
        # Query metrics with summary
        query = MetricsQuery(limit=10)
        results = metrics_engine.query_metrics(query)
        
        # Should have summary
        assert results.summary is not None
        assert isinstance(results.summary, BundleMetricsSummary)
        assert results.summary.total_snapshots == 3
        assert 0 <= results.summary.avg_risk_score <= 1
        assert results.summary.high_risk_count >= 0
        assert results.summary.critical_risk_count >= 0
    
    def test_audit_logging(self, metrics_engine, sample_snapshot):
        """Test audit logging during metrics computation"""
        initial_count = len(metrics_engine.audit_logger._audit_trail)
        
        metrics = metrics_engine.compute_metrics(sample_snapshot)
        
        # Should have logged metrics computation
        assert len(metrics_engine.audit_logger._audit_trail) > initial_count
        
        # Find the metrics computation log
        metrics_logs = metrics_engine.audit_logger.get_audit_trail(action="metrics_computed")
        assert len(metrics_logs) >= 1
        
        log = metrics_logs[-1]
        assert log.snapshot_id == sample_snapshot.snapshot_id
        assert log.member_id == sample_snapshot.member_id
        assert log.refill_id == sample_snapshot.refill_id
        assert log.processing_time_ms is not None
        assert log.details["risk_score"] == metrics.overall_risk_score
    
    def test_deterministic_computation(self, metrics_engine, sample_snapshot):
        """Test that metrics computation is deterministic"""
        # Compute metrics twice
        metrics1 = metrics_engine.compute_metrics(sample_snapshot)
        metrics2 = metrics_engine.compute_metrics(sample_snapshot)
        
        # Should be identical except for timestamp and computation time
        assert metrics1.snapshot_id == metrics2.snapshot_id
        assert metrics1.overall_risk_score == metrics2.overall_risk_score
        assert metrics1.risk_severity == metrics2.risk_severity
        assert metrics1.age_in_stage.current_stage == metrics2.age_in_stage.current_stage
        assert metrics1.timing_overlap.bundle_size == metrics2.timing_overlap.bundle_size
        assert metrics1.refill_gap.days_since_last_fill == metrics2.refill_gap.days_since_last_fill
        assert metrics1.bundle_alignment.bundle_alignment_score == metrics2.bundle_alignment.bundle_alignment_score
    
    def test_performance_metrics(self, metrics_engine, sample_bundle_snapshots):
        """Test performance metrics computation"""
        import time
        
        # Measure batch computation time
        start_time = time.time()
        metrics_list = metrics_engine.compute_batch_metrics(sample_bundle_snapshots)
        end_time = time.time()
        
        # Should complete quickly
        computation_time = end_time - start_time
        assert computation_time < 1.0  # Should complete in less than 1 second
        
        # Each metric should have computation time recorded
        total_computation_time = sum(m.computation_time_ms for m in metrics_list)
        assert total_computation_time > 0
        
        # Average computation time should be reasonable
        avg_time = total_computation_time / len(metrics_list)
        assert avg_time < 100  # Less than 100ms per metric
