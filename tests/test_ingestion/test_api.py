"""
Tests for ingestion API endpoints.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from src.ingestion.api import IngestionAPI, create_ingestion_api
from src.ingestion.processors import ProcessingResult
from src.models.events import EventType, EventSource


class TestIngestionAPI:
    """Test IngestionAPI class and endpoints"""
    
    @pytest.fixture
    def api_client(self):
        """Create test client for API"""
        app = create_ingestion_api()
        return TestClient(app)
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock event processor"""
        processor = Mock()
        processor.process_single_event = Mock(return_value=ProcessingResult(
            success=True,
            processed_events=[],
            validation_errors=[],
            processing_errors=[],
            processing_time_ms=50
        ))
        processor.process_batch = Mock(return_value=ProcessingResult(
            success=True,
            processed_events=[],
            validation_errors=[],
            processing_errors=[],
            processing_time_ms=100,
            batch_id="test_batch_123"
        ))
        processor.audit_logger = Mock()
        processor.audit_logger.get_audit_trail = Mock(return_value=[])
        processor.get_processing_statistics = Mock(return_value={"total_records": 0})
        processor.get_batch_details = Mock(return_value={"batch_id": "test_batch_123"})
        processor.get_event_lineage = Mock(return_value=[])
        return processor
    
    @pytest.fixture
    def api_client_with_mock(self, mock_processor):
        """Create test client with mocked processor"""
        api = IngestionAPI(processor=mock_processor)
        return TestClient(api.get_app()), api
    
    def test_ingest_single_event_success(self, api_client_with_mock, sample_refill_event_data):
        """Test successful single event ingestion"""
        client, api = api_client_with_mock
        response = client.post(
            "/ingest/event",
            json={
                "event_data": sample_refill_event_data,
                "source_system": "test_system"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["processing_time_ms"] >= 0
        assert data["event_id"] == sample_refill_event_data["event_id"]
        assert len(data["validation_errors"]) == 0
        assert len(data["processing_errors"]) == 0
    
    def test_ingest_single_event_validation_error(self, api_client_with_mock):
        """Test single event ingestion with validation error"""
        client, api = api_client_with_mock
        # Mock processor to return validation error
        api.processor.process_single_event.return_value = ProcessingResult(
            success=False,
            processed_events=[],
            validation_errors=[{"errors": ["Missing required field"]}],
            processing_errors=[{"error": "Processing failed"}],
            processing_time_ms=25
        )
        
        response = client.post(
            "/ingest/event",
            json={
                "event_data": {"invalid": "data"},
                "source_system": "test_system"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert len(data["validation_errors"]) == 1
        assert "Missing required field" in str(data["validation_errors"])
    
    def test_ingest_single_event_processing_error(self, api_client_with_mock):
        """Test single event ingestion with processing error"""
        client, api = api_client_with_mock
        # Mock processor to return processing error
        api.processor.process_single_event.return_value = ProcessingResult(
            success=False,
            processed_events=[],
            validation_errors=[],
            processing_errors=[{"event_id": "test", "error": "Processing failed"}],
            processing_time_ms=15
        )
        
        response = client.post(
            "/ingest/event",
            json={
                "event_data": {"event_id": "test_event_1234567890"},
                "source_system": "test_system"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert len(data["processing_errors"]) == 1
        assert "Processing failed" in data["processing_errors"][0]
    
    def test_ingest_batch_success(self, api_client_with_mock, sample_refill_event_data, sample_pa_event_data):
        """Test successful batch ingestion"""
        client, api = api_client_with_mock
        batch_data = [sample_refill_event_data, sample_pa_event_data]
        
        response = client.post(
            "/ingest/batch",
            json={
                "events": batch_data,
                "source_system": "test_system",
                "batch_size_limit": 10000
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["total_events"] == 2
        assert data["processed_events"] == 0  # Mock returns empty
        assert data["validation_errors"] == 0
        assert data["processing_errors"] == 0
        assert data["batch_id"] == "test_batch_123"
        assert data["processing_time_ms"] >= 0
    
    def test_ingest_batch_size_limit_exceeded(self, api_client_with_mock):
        """Test batch ingestion with size limit exceeded"""
        client, api = api_client_with_mock
        # Create batch larger than limit
        large_batch = [{"event_id": f"evt_{i:010d}", "member_id": f"mem_{i:010d}", 
                        "refill_id": f"ref_{i:010d}", "event_type": "refill_initiated",
                        "event_source": "centersync", "event_timestamp": datetime.now(timezone.utc).isoformat(),
                        "received_timestamp": datetime.now(timezone.utc).isoformat()} 
                       for i in range(10001)]
        
        response = client.post(
            "/ingest/batch",
            json={
                "events": large_batch,
                "source_system": "test_system",
                "batch_size_limit": 10000
            }
        )
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "exceeds limit" in response.json()["detail"]
    
    def test_ingest_batch_validation_errors(self, api_client_with_mock):
        """Test batch ingestion with validation errors"""
        client, api = api_client_with_mock
        # Mock processor to return validation errors
        api.processor.process_batch.return_value = ProcessingResult(
            success=False,
            processed_events=[],
            validation_errors=[{"event_id": "test1", "errors": ["Invalid field"]}],
            processing_errors=[],
            processing_time_ms=75,
            batch_id="test_batch_456"
        )
        
        response = client.post(
            "/ingest/batch",
            json={
                "events": [{"event_id": "test_event_1234567890"}],
                "source_system": "test_system"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["validation_errors"] == 1
        assert len(data["invalid_events"]) == 1
        assert "Invalid field" in data["invalid_events"][0]["errors"][0]
    
    def test_health_check(self, api_client_with_mock):
        """Test healthy health check"""
        client, api = api_client_with_mock
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"
        assert "audit_stats" in data
    
    def test_health_check_unhealthy(self, api_client_with_mock):
        """Test unhealthy health check"""
        client, api = api_client_with_mock
        # Mock processor to raise exception
        api.processor.get_processing_statistics.side_effect = Exception("Health check failed")
        
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data["audit_stats"]
    
    def test_get_audit_trail_success(self, api_client_with_mock):
        """Test successful audit trail retrieval"""
        client, api = api_client_with_mock
        # Mock audit trail
        mock_records = [
            Mock(to_dict=lambda: {"audit_id": "audit_1", "action": "event_received"}),
            Mock(to_dict=lambda: {"audit_id": "audit_2", "action": "event_processed"})
        ]
        api.processor.audit_logger.get_audit_trail.return_value = mock_records
        
        response = client.post(
            "/audit/trail",
            json={
                "event_id": "test_event_123",
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "audit_trail" in data
        assert len(data["audit_trail"]) == 2
        assert data["total_records"] == 2
        assert data["filters_applied"]["event_id"] == "test_event_123"
    
    def test_get_audit_trail_invalid_action(self, api_client_with_mock):
        """Test audit trail retrieval with invalid action"""
        client, api = api_client_with_mock
        response = client.post(
            "/audit/trail",
            json={
                "action": "invalid_action",
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid action" in response.json()["detail"]
    
    def test_get_event_lineage_success(self, api_client_with_mock):
        """Test successful event lineage retrieval"""
        client, api = api_client_with_mock
        # Mock lineage
        mock_lineage = [
            {"audit_id": "audit_1", "action": "event_received", "event_id": "test_event"},
            {"audit_id": "audit_2", "action": "event_processed", "event_id": "test_event"}
        ]
        api.processor.get_event_lineage.return_value = mock_lineage
        
        response = client.get("/audit/event/test_event/lineage")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["event_id"] == "test_event"
        assert len(data["lineage"]) == 2
        assert data["total_records"] == 2
    
    def test_get_batch_details_success(self, api_client_with_mock):
        """Test successful batch details retrieval"""
        client, api = api_client_with_mock
        mock_details = {
            "batch_id": "test_batch_123",
            "total_records": 5,
            "actions": ["batch_received", "batch_processed"]
        }
        api.processor.get_batch_details.return_value = mock_details
        
        response = client.get("/audit/batch/test_batch_123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["batch_id"] == "test_batch_123"
        assert data["total_records"] == 5
    
    def test_get_processing_statistics_success(self, api_client_with_mock):
        """Test successful processing statistics retrieval"""
        client, api = api_client_with_mock
        mock_stats = {
            "total_records": 100,
            "processed_events": 95,
            "failed_validations": 3,
            "failed_processing": 2,
            "success_rate": 0.95
        }
        api.processor.get_processing_statistics.return_value = mock_stats
        
        response = client.get("/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_records"] == 100
        assert data["success_rate"] == 0.95
    
    def test_export_audit_trail_success(self, api_client_with_mock):
        """Test successful audit trail export"""
        client, api = api_client_with_mock
        # Mock export
        api.processor.audit_logger.export_audit_trail.return_value = {"test": "data"}
        
        response = client.get("/audit/export?format=json")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-disposition"] == "attachment; filename=audit_trail.json"
        assert response.json() == {"test": "data"}
    
    def test_export_audit_trail_invalid_format(self, api_client_with_mock):
        """Test audit trail export with invalid format"""
        client, api = api_client_with_mock
        response = client.get("/audit/export?format=xml")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported format" in response.json()["detail"]
    
    def test_server_error_handling(self, api_client_with_mock):
        """Test server error handling"""
        client, api = api_client_with_mock
        # Mock processor to raise exception
        api.processor.process_single_event.side_effect = Exception("Server error")
        
        response = client.post(
            "/ingest/event",
            json={
                "event_data": {"event_id": "test_event_1234567890"},
                "source_system": "test_system"
            }
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Event ingestion failed" in response.json()["detail"]


class TestAPIIntegration:
    """Integration tests for API with real processor"""
    
    @pytest.fixture
    def integration_client(self):
        """Create test client with real processor"""
        app = create_ingestion_api()
        return TestClient(app)
    
    def test_integration_single_event(self, integration_client, sample_refill_event_data):
        """Integration test for single event ingestion"""
        response = integration_client.post(
            "/ingest/event",
            json={
                "event_data": sample_refill_event_data,
                "source_system": "integration_test"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == sample_refill_event_data["event_id"]
    
    def test_integration_batch_events(self, integration_client, sample_refill_event_data, sample_pa_event_data):
        """Integration test for batch event ingestion"""
        batch_data = [sample_refill_event_data, sample_pa_event_data]
        
        response = integration_client.post(
            "/ingest/batch",
            json={
                "events": batch_data,
                "source_system": "integration_test"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["total_events"] == 2
        assert data["batch_id"] is not None
    
    def test_integration_health_check(self, integration_client):
        """Integration test for health check"""
        response = integration_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "audit_stats" in data
