"""
Tests for Snapshot Aggregation Engine
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from src.models.events import (
    BaseCanonicalEvent, RefillEvent, PAEvent, OSEvent, BundleEvent,
    EventType, EventSource, RefillStatus, PAStatus
)
from src.models.snapshots import (
    RefillSnapshot, SnapshotStage, PAState, BundleTimingState,
    SnapshotQuery, SnapshotList
)
from src.aggregation.snapshot_engine import SnapshotAggregationEngine
from src.utils.audit import AuditLogger


class TestSnapshotAggregationEngine:
    """Test cases for snapshot aggregation engine"""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing"""
        return AuditLogger()
    
    @pytest.fixture
    def snapshot_engine(self, audit_logger):
        """Create snapshot engine for testing"""
        return SnapshotAggregationEngine(audit_logger=audit_logger)
    
    @pytest.fixture
    def sample_utc_datetime(self):
        """Sample UTC datetime for testing"""
        from datetime import timezone
        return datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    @pytest.fixture
    def base_event_data(self, sample_utc_datetime):
        """Base event data for testing"""
        return {
            "event_id": "evt_test_1234567890abcdef",
            "member_id": "mem_test_1234567890abcdef",
            "refill_id": "ref_test_1234567890abcdef",
            "bundle_id": "bun_test_1234567890abcdef",
            "event_type": EventType.REFILL_INITIATED,
            "event_source": EventSource.CENTERSYNC,
            "event_timestamp": sample_utc_datetime,
            "received_timestamp": sample_utc_datetime,
            "source_event_id": "src_evt_123",
            "source_system": "centersync",
            "source_timestamp": sample_utc_datetime,
            "bundle_member_count": 2,
            "bundle_refill_count": 3,
            "bundle_sequence": 1,
            "correlation_id": "corr_1234567890abcdef",
            "causation_id": "caus_1234567890abcdef"
        }
    
    @pytest.fixture
    def sample_refill_events(self, base_event_data, sample_utc_datetime):
        """Sample refill events for testing"""
        events = []
        
        # Initiation event
        initiation_data = base_event_data.copy()
        initiation_data["event_id"] = "evt_init_1234567890abcdef"
        initiation_data["event_type"] = EventType.REFILL_INITIATED
        initiation_data["event_timestamp"] = sample_utc_datetime
        initiation_data["drug_ndc"] = "123456789012"
        initiation_data["drug_name"] = "Lisinopril"
        initiation_data["days_supply"] = 30
        initiation_data["quantity"] = 10.0
        initiation_data["refill_due_date"] = sample_utc_datetime + timedelta(days=30)
        initiation_data["ship_by_date"] = sample_utc_datetime + timedelta(days=25)
        initiation_data["last_fill_date"] = sample_utc_datetime - timedelta(days=60)
        initiation_data["refill_status"] = RefillStatus.PENDING
        initiation_data["source_status"] = "INITIATED"
        initiation_data["days_until_due"] = 30
        initiation_data["days_since_last_fill"] = 60
        initiation_data["bundle_alignment_score"] = 0.85
        
        events.append(RefillEvent(**initiation_data))
        
        # Eligibility event
        eligibility_data = base_event_data.copy()
        eligibility_data["event_id"] = "evt_elig_1234567890abcdef"
        eligibility_data["event_type"] = EventType.REFILL_ELIGIBLE
        eligibility_data["event_timestamp"] = sample_utc_datetime + timedelta(hours=2)
        eligibility_data["refill_status"] = RefillStatus.ELIGIBLE
        eligibility_data["source_status"] = "ELIGIBLE_FOR_BUNDLING"
        eligibility_data["days_until_due"] = 29
        eligibility_data["days_since_last_fill"] = 60
        eligibility_data["bundle_alignment_score"] = 0.90
        
        events.append(RefillEvent(**eligibility_data))
        
        # Bundle event
        bundle_data = base_event_data.copy()
        bundle_data["event_id"] = "evt_bund_1234567890abcdef"
        bundle_data["event_type"] = EventType.REFILL_BUNDLED
        bundle_data["event_timestamp"] = sample_utc_datetime + timedelta(hours=4)
        bundle_data["refill_status"] = RefillStatus.BUNDLED
        bundle_data["source_status"] = "BUNDLED"
        bundle_data["days_until_due"] = 28
        bundle_data["days_since_last_fill"] = 60
        bundle_data["bundle_alignment_score"] = 0.95
        
        events.append(RefillEvent(**bundle_data))
        
        return events
    
    @pytest.fixture
    def sample_pa_events(self, base_event_data, sample_utc_datetime):
        """Sample PA events for testing"""
        events = []
        
        # PA submission
        pa_sub_data = base_event_data.copy()
        pa_sub_data["event_id"] = "evt_pa_sub_1234567890abcdef"
        pa_sub_data["event_type"] = EventType.PA_SUBMITTED
        pa_sub_data["event_timestamp"] = sample_utc_datetime + timedelta(hours=6)
        pa_sub_data["pa_status"] = PAStatus.SUBMITTED
        pa_sub_data["pa_type"] = "new"
        pa_sub_data["pa_submitted_date"] = sample_utc_datetime + timedelta(hours=6)
        pa_sub_data["pa_processing_days"] = 0
        pa_sub_data["pa_validity_days"] = 90
        pa_sub_data["pa_reason_code"] = "FORMULARY"
        
        events.append(PAEvent(**pa_sub_data))
        
        # PA approval
        pa_app_data = base_event_data.copy()
        pa_app_data["event_id"] = "evt_pa_app_1234567890abcdef"
        pa_app_data["event_type"] = EventType.PA_APPROVED
        pa_app_data["event_timestamp"] = sample_utc_datetime + timedelta(days=2)
        pa_app_data["pa_status"] = PAStatus.APPROVED
        pa_app_data["pa_type"] = "new"
        pa_app_data["pa_submitted_date"] = sample_utc_datetime + timedelta(hours=6)
        pa_app_data["pa_response_date"] = sample_utc_datetime + timedelta(days=2)
        pa_app_data["pa_expiry_date"] = sample_utc_datetime + timedelta(days=92)
        pa_app_data["pa_processing_days"] = 2
        pa_app_data["pa_validity_days"] = 90
        pa_app_data["pa_reason_code"] = "FORMULARY"
        
        events.append(PAEvent(**pa_app_data))
        
        return events
    
    @pytest.fixture
    def sample_oos_events(self, base_event_data, sample_utc_datetime):
        """Sample OOS events for testing"""
        events = []
        
        # OOS detected
        oos_det_data = base_event_data.copy()
        oos_det_data["event_id"] = "evt_oos_det_1234567890abcdef"
        oos_det_data["event_type"] = EventType.OOS_DETECTED
        oos_det_data["event_timestamp"] = sample_utc_datetime + timedelta(days=5)
        oos_det_data["oos_status"] = "DETECTED"
        oos_det_data["drug_ndc"] = "123456789012"
        oos_det_data["drug_name"] = "Lisinopril"
        oos_det_data["oos_reason"] = "MANUFACTURER_SHORTAGE"
        oos_det_data["oos_detected_date"] = sample_utc_datetime + timedelta(days=5)
        oos_det_data["estimated_resupply_date"] = sample_utc_datetime + timedelta(days=10)
        oos_det_data["alternative_available"] = True
        
        events.append(OSEvent(**oos_det_data))
        
        # OOS resolved
        oos_res_data = base_event_data.copy()
        oos_res_data["event_id"] = "evt_oos_res_1234567890abcdef"
        oos_res_data["event_type"] = EventType.OOS_RESOLVED
        oos_res_data["event_timestamp"] = sample_utc_datetime + timedelta(days=8)
        oos_res_data["oos_status"] = "RESOLVED"
        oos_res_data["drug_ndc"] = "123456789012"
        oos_res_data["drug_name"] = "Lisinopril"
        oos_res_data["oos_reason"] = "MANUFACTURER_SHORTAGE"
        oos_res_data["oos_resolved_date"] = sample_utc_datetime + timedelta(days=8)
        oos_res_data["oos_duration_days"] = 3
        
        events.append(OSEvent(**oos_res_data))
        
        return events
    
    @pytest.fixture
    def sample_bundle_events(self, base_event_data, sample_utc_datetime):
        """Sample bundle events for testing"""
        events = []
        
        # Bundle formed
        bundle_form_data = base_event_data.copy()
        bundle_form_data["event_id"] = "evt_bun_form_1234567890abcdef"
        bundle_form_data["event_type"] = EventType.BUNDLE_FORMED
        bundle_form_data["event_timestamp"] = sample_utc_datetime + timedelta(hours=4)
        bundle_form_data["total_refills"] = 3
        bundle_form_data["total_members"] = 2
        bundle_form_data["bundle_strategy"] = "TIMING_ALIGNED"
        bundle_form_data["bundle_efficiency_score"] = 0.85
        bundle_form_data["split_risk_score"] = 0.15
        
        events.append(BundleEvent(**bundle_form_data))
        
        # Bundle shipped
        bundle_ship_data = base_event_data.copy()
        bundle_ship_data["event_id"] = "evt_bun_ship_1234567890abcdef"
        bundle_ship_data["event_type"] = EventType.BUNDLE_SHIPPED
        bundle_ship_data["event_timestamp"] = sample_utc_datetime + timedelta(days=10)
        bundle_ship_data["total_refills"] = 3
        bundle_ship_data["total_members"] = 2
        bundle_ship_data["bundle_strategy"] = "TIMING_ALIGNED"
        bundle_ship_data["bundle_efficiency_score"] = 0.90
        bundle_ship_data["bundle_ship_date"] = sample_utc_datetime + timedelta(days=10)
        
        events.append(BundleEvent(**bundle_ship_data))
        
        return events
    
    def test_aggregate_refill_events_only(self, snapshot_engine, sample_refill_events):
        """Test aggregating only refill events"""
        snapshot = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        # Verify basic snapshot properties
        assert snapshot.snapshot_id.startswith("snapshot_")
        assert snapshot.member_id == "mem_test_1234567890abcdef"
        assert snapshot.refill_id == "ref_test_1234567890abcdef"
        assert snapshot.bundle_id == "bun_test_1234567890abcdef"
        
        # Verify event counts
        assert snapshot.total_events == 3
        assert snapshot.refill_events == 3
        assert snapshot.pa_events == 0
        assert snapshot.oos_events == 0
        assert snapshot.bundle_events == 0
        
        # Verify refill details
        assert snapshot.drug_ndc == "123456789012"
        assert snapshot.drug_name == "Lisinopril"
        assert snapshot.days_supply == 30
        assert snapshot.quantity == 10.0
        
        # Verify timing
        assert snapshot.refill_due_date is not None
        assert snapshot.ship_by_date is not None
        assert snapshot.last_fill_date is not None
        
        # Verify status
        assert snapshot.refill_status == RefillStatus.BUNDLED
        assert snapshot.source_status == "BUNDLED"
        
        # Verify bundle context
        assert snapshot.bundle_member_count == 2
        assert snapshot.bundle_refill_count == 3
        assert snapshot.bundle_sequence == 1
        assert snapshot.bundle_alignment_score == 0.95
        
        # Verify key timestamps
        assert snapshot.initiated_timestamp is not None
        assert snapshot.eligible_timestamp is not None
        assert snapshot.bundled_timestamp is not None
        assert snapshot.shipped_timestamp is None
        assert snapshot.completed_timestamp is None
        
        # Verify current stage
        assert snapshot.current_stage == SnapshotStage.BUNDLED
        assert snapshot.pa_state == PAState.NOT_REQUIRED
        assert snapshot.bundle_timing_state == BundleTimingState.ALIGNED
    
    def test_aggregate_events_with_pa(self, snapshot_engine, sample_refill_events, sample_pa_events):
        """Test aggregating events with PA"""
        all_events = sample_refill_events + sample_pa_events
        snapshot = snapshot_engine.aggregate_events_to_snapshot(all_events)
        
        # Verify event counts
        assert snapshot.total_events == 5
        assert snapshot.refill_events == 3
        assert snapshot.pa_events == 2
        
        # Verify PA information
        assert snapshot.pa_type == "new"
        assert snapshot.pa_processing_days == 2
        assert snapshot.pa_expiry_date is not None
        
        # Verify PA timestamps
        assert snapshot.pa_submitted_timestamp is not None
        assert snapshot.pa_resolved_timestamp is not None
        
        # Verify PA state
        assert snapshot.pa_state == PAState.APPROVED
    
    def test_aggregate_events_with_oos(self, snapshot_engine, sample_refill_events, sample_oos_events):
        """Test aggregating events with OOS"""
        all_events = sample_refill_events + sample_oos_events
        snapshot = snapshot_engine.aggregate_events_to_snapshot(all_events)
        
        # Verify event counts
        assert snapshot.total_events == 5
        assert snapshot.refill_events == 3
        assert snapshot.oos_events == 2
        
        # Verify OOS timestamps
        assert snapshot.oos_detected_timestamp is not None
        assert snapshot.oos_resolved_timestamp is not None
        
        # Verify current stage (should be BUNDLED since OOS is resolved)
        assert snapshot.current_stage == SnapshotStage.BUNDLED
    
    def test_aggregate_events_with_bundle(self, snapshot_engine, sample_refill_events, sample_bundle_events):
        """Test aggregating events with bundle events"""
        all_events = sample_refill_events + sample_bundle_events
        snapshot = snapshot_engine.aggregate_events_to_snapshot(all_events)
        
        # Verify event counts
        assert snapshot.total_events == 5
        assert snapshot.refill_events == 3
        assert snapshot.bundle_events == 2
        
        # Verify bundle timestamps
        assert snapshot.bundled_timestamp is not None
        assert snapshot.shipped_timestamp is not None
        
        # Verify current stage (should be SHIPPED)
        assert snapshot.current_stage == SnapshotStage.SHIPPED
    
    def test_aggregate_complete_lifecycle(self, snapshot_engine, sample_refill_events, 
                                         sample_pa_events, sample_oos_events, sample_bundle_events):
        """Test aggregating complete refill lifecycle"""
        all_events = sample_refill_events + sample_pa_events + sample_oos_events + sample_bundle_events
        snapshot = snapshot_engine.aggregate_events_to_snapshot(all_events)
        
        # Verify event counts
        assert snapshot.total_events == 9  # 3 refill + 2 PA + 2 OOS + 2 bundle (note: evt_bund from refill events and evt_bun_form from bundle events are different)
        assert snapshot.refill_events == 3
        assert snapshot.pa_events == 2
        assert snapshot.oos_events == 2
        assert snapshot.bundle_events == 2
        
        # Verify current stage (should be SHIPPED)
        assert snapshot.current_stage == SnapshotStage.SHIPPED
        assert snapshot.pa_state == PAState.APPROVED
        assert snapshot.bundle_timing_state == BundleTimingState.ALIGNED
        
        # Verify timing metrics
        assert snapshot.days_until_due is not None
        assert snapshot.days_since_last_fill is not None
        assert snapshot.total_processing_days is not None
        assert snapshot.days_in_current_stage is not None
        
        # Verify event IDs
        assert len(snapshot.event_ids) == 9
        assert all(eid.startswith("evt_") for eid in snapshot.event_ids)
    
    def test_aggregate_empty_events(self, snapshot_engine):
        """Test error handling for empty events"""
        with pytest.raises(ValueError, match="Cannot create snapshot from empty event list"):
            snapshot_engine.aggregate_events_to_snapshot([])
    
    def test_get_snapshot(self, snapshot_engine, sample_refill_events):
        """Test retrieving snapshot by ID"""
        snapshot = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        retrieved = snapshot_engine.get_snapshot(snapshot.snapshot_id)
        
        assert retrieved is not None
        assert retrieved.snapshot_id == snapshot.snapshot_id
        assert retrieved.member_id == snapshot.member_id
        assert retrieved.refill_id == snapshot.refill_id
    
    def test_get_nonexistent_snapshot(self, snapshot_engine):
        """Test retrieving non-existent snapshot"""
        retrieved = snapshot_engine.get_snapshot("nonexistent")
        assert retrieved is None
    
    def test_query_snapshots_by_member(self, snapshot_engine, sample_refill_events):
        """Test querying snapshots by member ID"""
        # Create snapshots for different members
        snapshot1 = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        # Create events for different member
        events2 = []
        for event in sample_refill_events:
            event_data = event.dict()
            event_data["member_id"] = "mem_different_1234567890abcdef"
            event_data["event_id"] = f"diff_{event.event_id}"
            events2.append(RefillEvent(**event_data))
        
        snapshot2 = snapshot_engine.aggregate_events_to_snapshot(events2)
        
        # Query by member
        query = SnapshotQuery(member_id="mem_test_1234567890abcdef")
        results = snapshot_engine.query_snapshots(query)
        
        assert results.total_count == 1
        assert len(results.snapshots) == 1
        assert results.snapshots[0].snapshot_id == snapshot1.snapshot_id
    
    def test_query_snapshots_by_stage(self, snapshot_engine, sample_refill_events):
        """Test querying snapshots by stage"""
        snapshot = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        query = SnapshotQuery(current_stage=SnapshotStage.BUNDLED)
        results = snapshot_engine.query_snapshots(query)
        
        assert results.total_count == 1
        assert len(results.snapshots) == 1
        assert results.snapshots[0].current_stage == SnapshotStage.BUNDLED
    
    def test_query_snapshots_pagination(self, snapshot_engine, sample_refill_events):
        """Test snapshot query pagination"""
        # Create multiple snapshots
        snapshots = []
        for i in range(5):
            events = []
            for event in sample_refill_events:
                event_data = event.dict()
                event_data["member_id"] = f"mem_test_{i:02d}_1234567890abcdef"
                event_data["refill_id"] = f"ref_test_{i:02d}_1234567890abcdef"
                event_data["event_id"] = f"evt_{i:02d}_{event.event_id}"
                events.append(RefillEvent(**event_data))
            snapshots.append(snapshot_engine.aggregate_events_to_snapshot(events))
        
        # Test pagination
        query = SnapshotQuery(limit=2, offset=0)
        results = snapshot_engine.query_snapshots(query)
        
        assert results.total_count == 5
        assert len(results.snapshots) == 2
        assert results.has_more is True
        
        # Test second page
        query2 = SnapshotQuery(limit=2, offset=2)
        results2 = snapshot_engine.query_snapshots(query2)
        
        assert results2.total_count == 5
        assert len(results2.snapshots) == 2
        assert results2.has_more is True
        
        # Test last page
        query3 = SnapshotQuery(limit=2, offset=4)
        results3 = snapshot_engine.query_snapshots(query3)
        
        assert results3.total_count == 5
        assert len(results3.snapshots) == 1
        assert results3.has_more is False
    
    def test_get_member_snapshots(self, snapshot_engine, sample_refill_events):
        """Test getting all snapshots for a member"""
        # Create multiple snapshots for same member
        snapshot1 = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        # Create another snapshot for same member
        events2 = []
        for event in sample_refill_events:
            event_data = event.dict()
            event_data["event_id"] = f"second_{event.event_id}"
            event_data["event_timestamp"] = event.event_timestamp + timedelta(hours=24)
            events2.append(RefillEvent(**event_data))
        
        snapshot2 = snapshot_engine.aggregate_events_to_snapshot(events2)
        
        # Get member snapshots
        member_snapshots = snapshot_engine.get_member_snapshots("mem_test_1234567890abcdef")
        
        assert len(member_snapshots) == 2
        assert all(s.member_id == "mem_test_1234567890abcdef" for s in member_snapshots)
        
        # Should be sorted by timestamp descending
        assert member_snapshots[0].snapshot_timestamp >= member_snapshots[1].snapshot_timestamp
    
    def test_get_bundle_snapshots(self, snapshot_engine, sample_refill_events):
        """Test getting all snapshots for a bundle"""
        snapshot = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        bundle_snapshots = snapshot_engine.get_bundle_snapshots("bun_test_1234567890abcdef")
        
        assert len(bundle_snapshots) == 1
        assert bundle_snapshots[0].bundle_id == "bun_test_1234567890abcdef"
        assert bundle_snapshots[0].snapshot_id == snapshot.snapshot_id
    
    def test_timing_metrics_computation(self, snapshot_engine, sample_refill_events):
        """Test timing metrics computation"""
        from datetime import timezone
        # Set specific dates for testing
        base_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        # Update events with specific timing
        events = []
        for event in sample_refill_events:
            event_data = event.dict()
            if event.event_type == EventType.REFILL_INITIATED:
                event_data["event_timestamp"] = base_time
                event_data["last_fill_date"] = base_time - timedelta(days=60)
                event_data["refill_due_date"] = base_time + timedelta(days=30)
            events.append(RefillEvent(**event_data))
        
        snapshot = snapshot_engine.aggregate_events_to_snapshot(events)
        
        # Verify timing metrics
        assert snapshot.days_since_last_fill >= 60  # At least 60 days since last fill
        assert snapshot.days_until_due <= 30       # At most 30 days until due
        assert snapshot.total_processing_days >= 0  # Days since initiation
    
    def test_deterministic_aggregation(self, snapshot_engine, sample_refill_events):
        """Test that aggregation is deterministic"""
        # Create snapshot twice
        snapshot1 = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        snapshot2 = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        # Should be identical except for timestamp and ID
        assert snapshot1.member_id == snapshot2.member_id
        assert snapshot1.refill_id == snapshot2.refill_id
        assert snapshot1.current_stage == snapshot2.current_stage
        assert snapshot1.total_events == snapshot2.total_events
        assert snapshot1.bundle_alignment_score == snapshot2.bundle_alignment_score
    
    def test_audit_logging(self, snapshot_engine, sample_refill_events, audit_logger):
        """Test audit logging during aggregation"""
        initial_count = len(audit_logger._audit_trail)
        
        snapshot = snapshot_engine.aggregate_events_to_snapshot(sample_refill_events)
        
        # Should have logged snapshot aggregation
        assert len(audit_logger._audit_trail) > initial_count
        
        # Find the aggregation log
        aggregation_logs = audit_logger.get_audit_trail(action="snapshot_aggregated")
        assert len(aggregation_logs) >= 1
        
        log = aggregation_logs[-1]
        assert log.snapshot_id == snapshot.snapshot_id
        assert log.member_id == snapshot.member_id
        assert log.refill_id == snapshot.refill_id
        assert log.processing_time_ms is not None
        assert log.details["events_count"] == len(sample_refill_events)
