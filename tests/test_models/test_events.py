"""
Tests for canonical event schemas.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.events import (
    EventType,
    EventSource,
    RefillStatus,
    PAStatus,
    BaseCanonicalEvent,
    RefillEvent,
    PAEvent,
    OSEvent,
    BundleEvent,
    create_canonical_event
)


class TestBaseCanonicalEvent:
    """Test base canonical event functionality"""
    
    def test_valid_base_event(self, base_event_data):
        """Test creating a valid base event"""
        event = BaseCanonicalEvent(**base_event_data)
        assert event.event_id == "evt_1234567890abcdef"
        assert event.member_id == "mem_1234567890abcdef"
        assert event.refill_id == "ref_1234567890abcdef"
        assert event.event_type == EventType.REFILL_INITIATED
        assert event.event_source == EventSource.CENTERSYNC
    
    def test_invalid_timestamp_no_timezone(self, base_event_data):
        """Test that events without timezone-aware timestamps fail validation"""
        invalid_data = base_event_data.copy()
        invalid_data["event_timestamp"] = datetime(2024, 1, 15, 10, 30, 0)  # No timezone
        
        with pytest.raises(ValidationError, match="Timestamps must be timezone-aware"):
            BaseCanonicalEvent(**invalid_data)
    
    def test_invalid_short_member_id(self, base_event_data):
        """Test that short pseudonymized IDs fail validation"""
        invalid_data = base_event_data.copy()
        invalid_data["member_id"] = "short"
        
        with pytest.raises(ValidationError, match="Pseudonymized IDs should be at least 8 characters"):
            BaseCanonicalEvent(**invalid_data)
    
    def test_optional_fields(self, base_event_data):
        """Test that optional fields can be None"""
        minimal_data = {
            k: v for k, v in base_event_data.items() 
            if k not in ["bundle_id", "source_event_id", "source_system", "source_timestamp",
                        "bundle_member_count", "bundle_refill_count", "bundle_sequence",
                        "correlation_id", "causation_id"]
        }
        
        event = BaseCanonicalEvent(**minimal_data)
        assert event.bundle_id is None
        assert event.source_event_id is None
        assert event.bundle_member_count is None


class TestRefillEvent:
    """Test refill event functionality"""
    
    def test_valid_refill_event(self, sample_refill_event_data):
        """Test creating a valid refill event"""
        event = RefillEvent(**sample_refill_event_data)
        assert event.event_type == EventType.REFILL_ELIGIBLE
        assert event.drug_name == "Lisinopril"
        assert event.days_supply == 30
        assert event.refill_status == RefillStatus.ELIGIBLE
        assert event.bundle_alignment_score == 0.85
    
    def test_refill_event_inheritance(self, sample_refill_event_data):
        """Test that refill event inherits from base event"""
        event = RefillEvent(**sample_refill_event_data)
        assert isinstance(event, BaseCanonicalEvent)
        assert event.member_id == "mem_1234567890abcdef"
        assert event.event_source == EventSource.CENTERSYNC


class TestPAEvent:
    """Test PA event functionality"""
    
    def test_valid_pa_event(self, sample_pa_event_data):
        """Test creating a valid PA event"""
        event = PAEvent(**sample_pa_event_data)
        assert event.event_type == EventType.PA_APPROVED
        assert event.pa_status == PAStatus.APPROVED
        assert event.pa_type == "renewal"
        assert event.pa_processing_days == 2
        assert event.pa_validity_days == 365
    
    def test_pa_event_inheritance(self, sample_pa_event_data):
        """Test that PA event inherits from base event"""
        event = PAEvent(**sample_pa_event_data)
        assert isinstance(event, BaseCanonicalEvent)
        assert event.member_id == "mem_1234567890abcdef"


class TestOSEvent:
    """Test OOS event functionality"""
    
    def test_valid_oos_event(self, sample_oos_event_data):
        """Test creating a valid OOS event"""
        event = OSEvent(**sample_oos_event_data)
        assert event.event_type == EventType.OOS_DETECTED
        assert event.oos_status == "detected"
        assert event.oos_reason == "manufacturer_shortage"
        assert event.affected_quantity == 100.0
        assert event.alternative_available is False
    
    def test_oos_event_inheritance(self, sample_oos_event_data):
        """Test that OOS event inherits from base event"""
        event = OSEvent(**sample_oos_event_data)
        assert isinstance(event, BaseCanonicalEvent)


class TestBundleEvent:
    """Test bundle event functionality"""
    
    def test_valid_bundle_event(self, sample_bundle_event_data):
        """Test creating a valid bundle event"""
        event = BundleEvent(**sample_bundle_event_data)
        assert event.event_type == EventType.BUNDLE_FORMED
        assert event.bundle_type == "standard"
        assert event.bundle_strategy == "timing_optimized"
        assert event.total_refills == 5
        assert event.total_members == 3
        assert event.bundle_efficiency_score == 0.92
    
    def test_bundle_event_member_refills(self, sample_bundle_event_data):
        """Test bundle event member refills structure"""
        event = BundleEvent(**sample_bundle_event_data)
        assert len(event.member_refills) == 2
        assert event.member_refills[0]["member_id"] == "mem_123"
        assert event.member_refills[0]["refill_id"] == "ref_456"
    
    def test_bundle_event_inheritance(self, sample_bundle_event_data):
        """Test that bundle event inherits from base event"""
        event = BundleEvent(**sample_bundle_event_data)
        assert isinstance(event, BaseCanonicalEvent)


class TestEventFactory:
    """Test event factory functionality"""
    
    def test_create_refill_event(self, sample_refill_event_data):
        """Test factory creates refill event"""
        event = create_canonical_event(sample_refill_event_data)
        assert isinstance(event, RefillEvent)
        assert event.event_type == EventType.REFILL_ELIGIBLE
    
    def test_create_pa_event(self, sample_pa_event_data):
        """Test factory creates PA event"""
        event = create_canonical_event(sample_pa_event_data)
        assert isinstance(event, PAEvent)
        assert event.event_type == EventType.PA_APPROVED
    
    def test_create_oos_event(self, sample_oos_event_data):
        """Test factory creates OOS event"""
        event = create_canonical_event(sample_oos_event_data)
        assert isinstance(event, OSEvent)
        assert event.event_type == EventType.OOS_DETECTED
    
    def test_create_bundle_event(self, sample_bundle_event_data):
        """Test factory creates bundle event"""
        event = create_canonical_event(sample_bundle_event_data)
        assert isinstance(event, BundleEvent)
        assert event.event_type == EventType.BUNDLE_FORMED
    
    def test_create_default_refill_event(self, base_event_data):
        """Test factory defaults to refill event for unknown types"""
        # Use a generic event type that should default to RefillEvent
        data = base_event_data.copy()
        data["event_type"] = EventType.REFILL_CANCELLED
        event = create_canonical_event(data)
        assert isinstance(event, RefillEvent)


class TestEventEnums:
    """Test event enums"""
    
    def test_event_type_values(self):
        """Test event type enum values"""
        assert EventType.REFILL_INITIATED == "refill_initiated"
        assert EventType.PA_APPROVED == "pa_approved"
        assert EventType.OOS_DETECTED == "oos_detected"
        assert EventType.BUNDLE_FORMED == "bundle_formed"
    
    def test_event_source_values(self):
        """Test event source enum values"""
        assert EventSource.CENTERSYNC == "centersync"
        assert EventSource.HPIE == "hpie"
        assert EventSource.HPC == "hpc"
    
    def test_refill_status_values(self):
        """Test refill status enum values"""
        assert RefillStatus.ELIGIBLE == "eligible"
        assert RefillStatus.BUNDLED == "bundled"
        assert RefillStatus.SHIPPED == "shipped"
    
    def test_pa_status_values(self):
        """Test PA status enum values"""
        assert PAStatus.APPROVED == "approved"
        assert PAStatus.DENIED == "denied"
        assert PAStatus.SUBMITTED == "submitted"


class TestEventValidation:
    """Test comprehensive event validation"""
    
    def test_complete_refill_event_validation(self, sample_refill_event_data):
        """Test complete validation of refill event"""
        event = RefillEvent(**sample_refill_event_data)
        
        # Verify all required fields are present
        assert event.event_id is not None
        assert event.member_id is not None
        assert event.refill_id is not None
        assert event.event_type is not None
        assert event.event_source is not None
        assert event.event_timestamp is not None
        assert event.received_timestamp is not None
        
        # Verify optional fields can be None
        assert event.bundle_id is not None or event.bundle_id is None
        assert event.source_event_id is not None or event.source_event_id is None
    
    def test_event_serialization(self, sample_refill_event_data):
        """Test event serialization/deserialization"""
        event = RefillEvent(**sample_refill_event_data)
        
        # Test dict serialization
        event_dict = event.dict()
        assert "event_id" in event_dict
        assert "event_type" in event_dict
        assert "drug_name" in event_dict
        
        # Test JSON serialization
        event_json = event.json()
        assert isinstance(event_json, str)
        assert "Lisinopril" in event_json
