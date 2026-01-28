"""
Tests for event processing logic.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.ingestion.processors import EventProcessor, ProcessingResult
from src.utils.audit import AuditLogger, AuditAction
from src.utils.validation import EventValidator
from src.models.events import EventType, EventSource


class TestEventProcessor:
    """Test EventProcessor functionality"""
    
    def test_process_single_valid_event(self, sample_refill_event_data):
        """Test processing a single valid event"""
        processor = EventProcessor()
        
        result = processor.process_single_event(
            event_data=sample_refill_event_data,
            source_system="test_system"
        )
        
        assert result.success is True
        assert len(result.processed_events) == 1
        assert len(result.validation_errors) == 0
        assert len(result.processing_errors) == 0
        assert result.processing_time_ms >= 0
        
        # Verify audit trail
        audit_trail = processor.audit_logger.get_audit_trail()
        assert len(audit_trail) >= 2  # received + processed
        
        received_records = [r for r in audit_trail if r.action == AuditAction.EVENT_RECEIVED]
        processed_records = [r for r in audit_trail if r.action == AuditAction.EVENT_PROCESSED]
        assert len(received_records) == 1
        assert len(processed_records) == 1
    
    def test_process_single_invalid_event(self, base_event_data):
        """Test processing a single invalid event"""
        processor = EventProcessor()
        
        # Create invalid event (missing required fields)
        invalid_event = {
            "event_id": "short",  # Too short
            "member_id": "mem_123",  # Missing other required fields
        }
        
        result = processor.process_single_event(
            event_data=invalid_event,
            source_system="test_system"
        )
        
        assert result.success is False
        assert len(result.processed_events) == 0
        assert len(result.validation_errors) > 0
        assert len(result.processing_errors) == 0
        
        # Verify audit trail shows validation failure
        audit_trail = processor.audit_logger.get_audit_trail()
        validation_failed = [r for r in audit_trail if r.action == AuditAction.VALIDATION_FAILED]
        assert len(validation_failed) == 1

    def test_rejects_non_pseudonymous_ids(self, base_event_data):
        """Reject non-pseudonymous identifiers"""
        processor = EventProcessor()

        invalid_event = base_event_data.copy()
        invalid_event["member_id"] = "john.doe@example.com"
        invalid_event["refill_id"] = "123-45-6789"

        result = processor.process_single_event(
            event_data=invalid_event,
            source_system="test_system"
        )

        assert result.success is False
        assert any("pseudonymized identifier" in err for err in result.validation_errors[0]["errors"])
    
    def test_process_single_event_with_exception(self, sample_refill_event_data):
        """Test processing event that raises exception during creation"""
        processor = EventProcessor()
        
        # Mock create_canonical_event to raise exception
        with patch('src.ingestion.processors.create_canonical_event', side_effect=Exception("Test error")):
            result = processor.process_single_event(
                event_data=sample_refill_event_data,
                source_system="test_system"
            )
            
            assert result.success is False
            assert len(result.processed_events) == 0
            assert len(result.processing_errors) == 1
            assert "Test error" in result.processing_errors[0]["error"]
    
    def test_process_batch_valid_events(self, sample_refill_event_data, sample_pa_event_data):
        """Test processing batch of valid events"""
        processor = EventProcessor()
        
        batch_data = [sample_refill_event_data, sample_pa_event_data]
        
        result = processor.process_batch(
            batch_data=batch_data,
            source_system="test_system"
        )
        
        assert result.success is True
        assert len(result.processed_events) == 2
        assert len(result.validation_errors) == 0
        assert len(result.processing_errors) == 0
        assert result.batch_id is not None
        assert result.processing_time_ms >= 0
        
        # Verify audit trail
        audit_trail = processor.audit_logger.get_audit_trail()
        batch_received = [r for r in audit_trail if r.action == AuditAction.BATCH_RECEIVED]
        batch_processed = [r for r in audit_trail if r.action == AuditAction.BATCH_PROCESSED]
        assert len(batch_received) == 1
        assert len(batch_processed) == 1
    
    def test_process_batch_mixed_events(self, sample_refill_event_data, sample_pa_event_data, base_event_data):
        """Test processing batch with mixed valid/invalid events"""
        processor = EventProcessor()
        
        # Create invalid event
        invalid_event = base_event_data.copy()
        invalid_event.pop("event_type")  # Missing required field
        
        batch_data = [sample_refill_event_data, invalid_event, sample_pa_event_data]
        
        result = processor.process_batch(
            batch_data=batch_data,
            source_system="test_system"
        )
        
        assert result.success is False  # Failed due to validation errors
        assert len(result.processed_events) == 2  # Only valid events processed
        assert len(result.validation_errors) == 1  # One invalid event
        assert len(result.processing_errors) == 0
        assert result.batch_id is not None
    
    def test_process_batch_empty(self):
        """Test processing empty batch"""
        processor = EventProcessor()
        
        result = processor.process_batch(
            batch_data=[],
            source_system="test_system"
        )
        
        assert result.success is False
        assert len(result.processed_events) == 0
        assert len(result.validation_errors) == 1
        assert "Batch is empty" in result.validation_errors[0]["batch_error"]
    
    def test_process_batch_with_duplicate_ids(self, sample_refill_event_data):
        """Test processing batch with duplicate event IDs"""
        processor = EventProcessor()
        
        # Create batch with duplicate IDs
        batch_data = [sample_refill_event_data, sample_refill_event_data]
        
        result = processor.process_batch(
            batch_data=batch_data,
            source_system="test_system"
        )
        
        assert result.success is False
        assert len(result.validation_errors) > 0
        # Should detect duplicate IDs
        duplicate_error = next((err for err in result.validation_errors if "Duplicate event IDs" in str(err)), None)
        assert duplicate_error is not None
    
    def test_get_processing_statistics(self, sample_refill_event_data):
        """Test getting processing statistics"""
        processor = EventProcessor()
        
        # Process some events
        processor.process_single_event(sample_refill_event_data, "test_system")
        processor.process_batch([sample_refill_event_data], "test_system")
        
        stats = processor.get_processing_statistics()
        
        assert "total_records" in stats
        assert "processed_events" in stats
        assert "failed_validations" in stats
        assert "failed_processing" in stats
        assert "success_rate" in stats
        assert stats["processed_events"] >= 1
    
    def test_get_event_lineage(self, sample_refill_event_data):
        """Test getting event lineage"""
        processor = EventProcessor()
        
        event_id = sample_refill_event_data["event_id"]
        processor.process_single_event(sample_refill_event_data, "test_system")
        
        lineage = processor.get_event_lineage(event_id)
        
        assert len(lineage) >= 2  # received + processed
        assert all(record["event_id"] == event_id for record in lineage)
        
        # Check for expected actions
        actions = [record["action"] for record in lineage]
        assert "event_received" in actions
        assert "event_processed" in actions
    
    def test_get_batch_details(self, sample_refill_event_data):
        """Test getting batch details"""
        processor = EventProcessor()
        
        result = processor.process_batch([sample_refill_event_data], "test_system")
        batch_id = result.batch_id
        
        batch_details = processor.get_batch_details(batch_id)
        
        assert batch_details["batch_id"] == batch_id
        assert "actions" in batch_details
        assert "total_records" in batch_details
        assert "start_time" in batch_details
        assert "end_time" in batch_details
        assert batch_details["total_records"] >= 2  # received + processed
    
    def test_event_enrichment(self, sample_refill_event_data):
        """Test event enrichment (placeholder)"""
        from src.ingestion.processors import EventEnricher
        
        enricher = EventEnricher()
        processor = EventProcessor()
        
        # Process event to get canonical event
        result = processor.process_single_event(sample_refill_event_data, "test_system")
        event = result.processed_events[0]
        
        # Enrich event
        enriched_event = enricher.enrich_event(event)
        
        # For now, enrichment is a no-op
        assert enriched_event == event
    
    def test_event_routing(self, sample_refill_event_data, sample_pa_event_data, sample_oos_event_data):
        """Test event routing"""
        from src.ingestion.processors import EventRouter
        
        router = EventRouter()
        processor = EventProcessor()
        
        # Process events to get canonical events
        refill_result = processor.process_single_event(sample_refill_event_data, "test_system")
        pa_result = processor.process_single_event(sample_pa_event_data, "test_system")
        oos_result = processor.process_single_event(sample_oos_event_data, "test_system")
        
        events = [refill_result.processed_events[0], pa_result.processed_events[0], oos_result.processed_events[0]]
        
        # Route events
        routed = router.route_batch(events)
        
        assert "refill_processor" in routed
        assert "pa_processor" in routed
        assert "oos_processor" in routed
        assert len(routed["refill_processor"]) == 1
        assert len(routed["pa_processor"]) == 1
        assert len(routed["oos_processor"]) == 1


class TestProcessingResult:
    """Test ProcessingResult dataclass"""
    
    def test_processing_result_creation(self):
        """Test creating ProcessingResult"""
        result = ProcessingResult(
            success=True,
            processed_events=[],
            validation_errors=[],
            processing_errors=[],
            processing_time_ms=100,
            batch_id="test_batch"
        )
        
        assert result.success is True
        assert result.processing_time_ms == 100
        assert result.batch_id == "test_batch"
    
    def test_processing_result_defaults(self):
        """Test ProcessingResult with defaults"""
        result = ProcessingResult(
            success=False,
            processed_events=[],
            validation_errors=[{"error": "test"}],
            processing_errors=[],
            processing_time_ms=50
        )
        
        assert result.success is False
        assert result.batch_id is None
        assert len(result.validation_errors) == 1
