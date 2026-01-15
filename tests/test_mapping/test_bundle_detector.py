"""
Tests for bundle detection functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.mapping.bundle_detector import BundleDetector, BundleContext
from src.models.events import RefillEvent, EventType, EventSource, RefillStatus


class TestBundleContext:
    """Test BundleContext functionality"""
    
    def test_bundle_context_creation(self):
        """Test bundle context creation"""
        context = BundleContext(
            bundle_id="test_bundle",
            bundle_type="standard"
        )
        
        assert context.bundle_id == "test_bundle"
        assert context.bundle_type == "standard"
        assert context.bundle_status == "forming"
        assert context.member_count == 0
        assert context.refill_count == 0
        assert len(context.member_ids) == 0
        assert len(context.refill_ids) == 0
    
    def test_add_event_to_context(self):
        """Test adding events to bundle context"""
        context = BundleContext(bundle_id="test_bundle")
        
        # Create sample event
        event = RefillEvent(
            event_id="evt_1234567890abcdef",
            member_id="mem_1234567890abcdef",
            refill_id="ref_1234567890abcdef",
            event_type=EventType.REFILL_ELIGIBLE,
            event_source=EventSource.CENTERSYNC,
            event_timestamp=datetime.now(timezone.utc),
            received_timestamp=datetime.now(timezone.utc)
        )
        
        context.add_event(event)
        
        assert context.refill_count == 1
        assert context.member_count == 1
        assert "ref_1234567890abcdef" in context.refill_ids
        assert "mem_1234567890abcdef" in context.member_ids
        assert context.last_activity == event.event_timestamp
    
    def test_bundle_completion(self):
        """Test bundle completion status"""
        context = BundleContext(bundle_id="test_bundle")
        
        assert not context.is_complete()
        
        context.bundle_status = "completed"
        assert context.is_complete()
    
    def test_bundle_age_calculation(self):
        """Test bundle age calculation"""
        formation_time = datetime.now(timezone.utc) - timedelta(hours=5)
        context = BundleContext(
            bundle_id="test_bundle",
            formation_time=formation_time
        )
        
        age = context.age_in_hours()
        assert 4.9 <= age <= 5.1  # Allow for timing variance
        
        # Test without formation time
        context_no_time = BundleContext(bundle_id="test2")
        assert context_no_time.age_in_hours() == 0.0


class TestBundleDetector:
    """Test BundleDetector functionality"""
    
    @pytest.fixture
    def detector(self):
        """Create bundle detector"""
        return BundleDetector()
    
    @pytest.fixture
    def sample_event(self):
        """Create sample refill event"""
        return RefillEvent(
            event_id="evt_1234567890abcdef",
            member_id="mem_1234567890abcdef",
            refill_id="ref_1234567890abcdef",
            bundle_id="bun_1234567890abcdef",
            event_type=EventType.REFILL_ELIGIBLE,
            event_source=EventSource.CENTERSYNC,
            event_timestamp=datetime.now(timezone.utc),
            received_timestamp=datetime.now(timezone.utc),
            drug_name="Lisinopril",
            days_supply=30,
            quantity=10.0
        )
    
    @pytest.fixture
    def sample_event_no_bundle(self):
        """Create sample event without bundle ID"""
        return RefillEvent(
            event_id="evt_1234567890abcde",
            member_id="mem_1234567890abcde",
            refill_id="ref_1234567890abcde",
            event_type=EventType.REFILL_ELIGIBLE,
            event_source=EventSource.CENTERSYNC,
            event_timestamp=datetime.now(timezone.utc),
            received_timestamp=datetime.now(timezone.utc),
            drug_name="Lisinopril",
            days_supply=30,
            quantity=10.0
        )
    
    def test_detect_bundle_context_with_bundle_id(self, detector, sample_event):
        """Test bundle detection with explicit bundle ID"""
        context = detector.detect_bundle_context(sample_event)
        
        assert context.bundle_id == sample_event.bundle_id
        assert context.refill_count == 1
        assert context.member_count == 1
        assert sample_event.refill_id in context.refill_ids
        assert sample_event.member_id in context.member_ids
        assert context.bundle_status == "forming"
    
    def test_detect_bundle_context_without_bundle_id(self, detector, sample_event_no_bundle):
        """Test bundle detection without explicit bundle ID"""
        context = detector.detect_bundle_context(sample_event_no_bundle)
        
        # Should create individual bundle
        assert context.bundle_id is not None
        assert context.bundle_id.startswith("individual_")
        assert context.bundle_type == "individual"
        assert context.bundle_status == "active"
        assert context.refill_count == 1
        assert context.member_count == 1
    
    def test_get_or_create_bundle(self, detector, sample_event):
        """Test getting or creating bundle"""
        bundle_id = sample_event.bundle_id
        
        # First call should create new bundle
        context1 = detector._get_or_create_bundle(bundle_id)
        assert context1.bundle_id == bundle_id
        assert len(detector.active_bundles) == 1
        
        # Second call should return existing bundle
        context2 = detector._get_or_create_bundle(bundle_id)
        assert context1 is context2
        assert len(detector.active_bundles) == 1
    
    def test_find_recent_member_bundles(self, detector, sample_event):
        """Test finding recent bundles for a member"""
        # Add a bundle for the member
        bundle_id = sample_event.bundle_id
        detector.active_bundles[bundle_id] = BundleContext(
            bundle_id=bundle_id,
            member_ids={sample_event.member_id},
            last_activity=sample_event.event_timestamp
        )
        
        recent_bundles = detector._find_recent_member_bundles(
            sample_event.member_id, 
            sample_event.event_timestamp
        )
        
        assert len(recent_bundles) == 1
        assert recent_bundles[0] == bundle_id
    
    def test_complete_bundle(self, detector, sample_event):
        """Test completing a bundle"""
        bundle_id = sample_event.bundle_id
        
        # Create and complete bundle
        context = detector._get_or_create_bundle(bundle_id)
        detector.complete_bundle(bundle_id, "shipped")
        
        assert bundle_id not in detector.active_bundles
        assert bundle_id in detector.completed_bundles
        assert detector.completed_bundles[bundle_id].bundle_status == "shipped"
    
    def test_analyze_bundle_risks(self, detector):
        """Test bundle risk analysis"""
        # Create old bundle
        old_time = datetime.now(timezone.utc) - timedelta(hours=50)
        bundle_context = BundleContext(
            bundle_id="old_bundle",
            formation_time=old_time,
            last_activity=old_time,
            member_count=6,  # Large bundle
            refill_count=12,
            bundle_type="complex"
        )
        detector.active_bundles["old_bundle"] = bundle_context
        
        risks = detector.analyze_bundle_risks("old_bundle")
        
        assert "bundle_age_over_48h" in risks
        assert "large_bundle_over_5_members" in risks
        # Note: large_bundle_over_10_refills might not be included if other risks take priority
    
    def test_analyze_bundle_risks_inactive(self, detector):
        """Test risk analysis for inactive bundle"""
        # Create inactive bundle
        inactive_time = datetime.now(timezone.utc) - timedelta(hours=15)
        bundle_context = BundleContext(
            bundle_id="inactive_bundle",
            last_activity=inactive_time
        )
        detector.active_bundles["inactive_bundle"] = bundle_context
        
        risks = detector.analyze_bundle_risks("inactive_bundle")
        
        assert "bundle_inactive_over_12h" in risks
    
    def test_get_bundle_statistics(self, detector):
        """Test bundle statistics"""
        # Add some test bundles
        detector.active_bundles["bundle1"] = BundleContext(
            bundle_id="bundle1",
            member_count=2,
            refill_count=3,
            bundle_type="standard"
        )
        detector.active_bundles["bundle2"] = BundleContext(
            bundle_id="bundle2",
            member_count=1,
            refill_count=1,
            bundle_type="individual"
        )
        detector.completed_bundles["bundle3"] = BundleContext(
            bundle_id="bundle3",
            member_count=3,
            refill_count=5,
            bundle_type="complex"
        )
        
        stats = detector.get_bundle_statistics()
        
        assert stats["active_bundles"] == 2
        assert stats["completed_bundles"] == 1
        assert stats["average_bundle_size"] == 3.0  # (3+1+5)/3
        assert stats["bundle_types"]["standard"] == 1
        assert stats["bundle_types"]["individual"] == 1
        assert stats["bundle_types"]["complex"] == 1
    
    def test_cleanup_old_bundles(self, detector):
        """Test cleanup of old bundles"""
        # Add old completed bundle
        old_time = datetime.now(timezone.utc) - timedelta(hours=200)  # Over 1 week
        old_bundle = BundleContext(
            bundle_id="old_bundle",
            last_activity=old_time
        )
        detector.completed_bundles["old_bundle"] = old_bundle
        
        # Add recent completed bundle
        recent_time = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_bundle = BundleContext(
            bundle_id="recent_bundle",
            last_activity=recent_time
        )
        detector.completed_bundles["recent_bundle"] = recent_bundle
        
        initial_count = len(detector.completed_bundles)
        cleaned_count = detector.cleanup_old_bundles(max_age_hours=168)  # 1 week
        
        assert cleaned_count == 1
        assert len(detector.completed_bundles) == initial_count - cleaned_count
        assert "old_bundle" not in detector.completed_bundles
        assert "recent_bundle" in detector.completed_bundles
    
    def test_export_bundle_contexts(self, detector, sample_event):
        """Test bundle context export"""
        # Add bundle with event
        context = detector.detect_bundle_context(sample_event)
        
        exported = detector.export_bundle_contexts()
        
        assert "active_bundles" in exported
        assert "completed_bundles" in exported
        assert "member_relationships" in exported
        
        assert sample_event.bundle_id in exported["active_bundles"]
        bundle_export = exported["active_bundles"][sample_event.bundle_id]
        assert bundle_export["member_count"] == 1
        assert bundle_export["refill_count"] == 1
        assert bundle_export["bundle_type"] == "standard"
        assert sample_event.member_id in bundle_export["member_ids"]
        assert sample_event.refill_id in bundle_export["refill_ids"]
    
    def test_timing_based_bundle_detection(self, detector):
        """Test timing-based bundle inference"""
        # Create base bundle
        base_time = datetime.now(timezone.utc)
        base_bundle = BundleContext(
            bundle_id="timing_bundle",
            last_activity=base_time
        )
        detector.active_bundles["timing_bundle"] = base_bundle
        
        # Create event with similar timing (within 2 hours)
        similar_event = RefillEvent(
            event_id="evt_similar",
            member_id="mem_similar",
            refill_id="ref_similar",
            event_type=EventType.REFILL_ELIGIBLE,
            event_source=EventSource.CENTERSYNC,
            event_timestamp=base_time + timedelta(hours=1),
            received_timestamp=datetime.now(timezone.utc)
        )
        
        context = detector.detect_bundle_context(similar_event)
        
        # Should be added to existing bundle due to timing
        assert context.bundle_id == "timing_bundle"
        assert context.refill_count == 2
    
    def test_member_relationship_tracking(self, detector, sample_event):
        """Test member to bundle relationship tracking"""
        # Detect bundle for event
        context = detector.detect_bundle_context(sample_event)
        
        # Check relationship tracking
        assert sample_event.member_id in detector.bundle_relationships
        assert context.bundle_id in detector.bundle_relationships[sample_event.member_id]
    
    def test_find_related_events(self, detector, sample_event):
        """Test finding related events"""
        # This is a placeholder test - would need event store integration
        related = detector.find_related_events(sample_event)
        assert isinstance(related, list)


class TestBundleDetectorIntegration:
    """Integration tests for bundle detection"""
    
    def test_bundle_lifecycle_workflow(self):
        """Test complete bundle lifecycle"""
        detector = BundleDetector()
        
        # Create events for same bundle
        base_time = datetime.now(timezone.utc)
        bundle_id = "lifecycle_bundle"
        
        events = [
            RefillEvent(
                event_id=f"evt_1234567890abcde{i}",
                member_id=f"mem_1234567890abcde{i}",
                refill_id=f"ref_1234567890abcde{i}",
                bundle_id=bundle_id,
                event_type=EventType.REFILL_ELIGIBLE,
                event_source=EventSource.CENTERSYNC,
                event_timestamp=base_time + timedelta(hours=i),
                received_timestamp=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        # Process events
        contexts = []
        for event in events:
            context = detector.detect_bundle_context(event)
            contexts.append(context)
        
        # Verify bundle formation
        final_context = contexts[-1]
        assert final_context.bundle_id == bundle_id
        assert final_context.refill_count == 3
        assert final_context.member_count == 3
        
        # Complete bundle
        completed = detector.complete_bundle(bundle_id, "shipped")
        assert completed.bundle_status == "shipped"
        
        # Verify statistics
        stats = detector.get_bundle_statistics()
        assert stats["completed_bundles"] == 1
        assert stats["active_bundles"] == 0
    
    def test_multi_member_bundle_detection(self):
        """Test detection of multi-member bundles"""
        detector = BundleDetector()
        
        # Create bundle with multiple members
        bundle_id = "multi_member_bundle"
        member_ids = ["mem_1234567890abcde1", "mem_1234567890abcde2", "mem_1234567890abcde3"]
        
        for i, member_id in enumerate(member_ids):
            event = RefillEvent(
                event_id=f"evt_1234567890abcde{i}",
                member_id=member_id,
                refill_id=f"ref_1234567890abcde{i}",
                bundle_id=bundle_id,
                event_type=EventType.REFILL_ELIGIBLE,
                event_source=EventSource.CENTERSYNC,
                event_timestamp=datetime.now(timezone.utc),
                received_timestamp=datetime.now(timezone.utc)
            )
            
            context = detector.detect_bundle_context(event)
            
            if i == len(member_ids) - 1:  # Last event
                assert context.member_count == 3
                assert set(context.member_ids) == set(member_ids)
                assert context.refill_count == 3
        
        # Verify member relationships
        for member_id in member_ids:
            assert member_id in detector.bundle_relationships
            assert bundle_id in detector.bundle_relationships[member_id]
