"""
Ingestion API for PharmIQ

REST API endpoints for batch event ingestion with validation and audit logging.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncio

from src.models.events import BaseCanonicalEvent
from src.ingestion.processors import EventProcessor, ProcessingResult
from src.utils.validation import ValidationResult
from src.utils.audit import AuditLogger


# Pydantic models for API requests/responses
class EventIngestionRequest(BaseModel):
    """Single event ingestion request"""
    event_data: Dict[str, Any] = Field(..., description="Canonical event data")
    source_system: Optional[str] = Field(None, description="Source system identifier")


class BatchIngestionRequest(BaseModel):
    """Batch event ingestion request"""
    events: List[Dict[str, Any]] = Field(..., description="List of canonical events")
    source_system: Optional[str] = Field(None, description="Source system identifier")
    batch_size_limit: Optional[int] = Field(10000, description="Maximum batch size")


class EventIngestionResponse(BaseModel):
    """Single event ingestion response"""
    success: bool
    event_id: Optional[str] = None
    processing_time_ms: int
    validation_errors: List[str] = []
    processing_errors: List[str] = []
    audit_id: Optional[str] = None


class BatchIngestionResponse(BaseModel):
    """Batch event ingestion response"""
    success: bool
    batch_id: Optional[str] = None
    total_events: int
    processed_events: int
    validation_errors: int
    processing_errors: int
    processing_time_ms: int
    invalid_events: List[Dict[str, Any]] = []
    audit_summary: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    audit_stats: Optional[Dict[str, Any]] = None


class AuditTrailRequest(BaseModel):
    """Audit trail query request"""
    event_id: Optional[str] = None
    batch_id: Optional[str] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    limit: Optional[int] = Field(100, ge=1, le=1000)


class IngestionAPI:
    """Main ingestion API class"""
    
    def __init__(self, processor: EventProcessor = None):
        self._processor = processor or EventProcessor()
        self.app = FastAPI(
            title="PharmIQ Ingestion API",
            description="Batch event ingestion with validation and audit logging",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self._setup_routes()
    
    @property
    def processor(self):
        """Access to the underlying processor for testing"""
        return self._processor
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.post("/ingest/event", response_model=EventIngestionResponse)
        async def ingest_single_event(request: EventIngestionRequest):
            """Ingest a single canonical event"""
            try:
                result = self._processor.process_single_event(
                    event_data=request.event_data,
                    source_system=request.source_system
                )
                
                # Get audit ID for tracking
                audit_records = self._processor.audit_logger.get_audit_trail(
                    event_id=request.event_data.get("event_id"),
                    limit=1
                )
                audit_id = audit_records[0].audit_id if audit_records else None
                
                return EventIngestionResponse(
                    success=result.success,
                    event_id=request.event_data.get("event_id"),
                    processing_time_ms=result.processing_time_ms,
                    validation_errors=[error for error_dict in result.validation_errors for error in error_dict["errors"]],
                    processing_errors=[error_dict["error"] for error_dict in result.processing_errors],
                    audit_id=audit_id
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Event ingestion failed: {str(e)}"
                )
        
        @self.app.post("/ingest/batch", response_model=BatchIngestionResponse)
        async def ingest_batch_events(request: BatchIngestionRequest, background_tasks: BackgroundTasks):
            """Ingest a batch of canonical events"""
            try:
                # Validate batch size
                if len(request.events) > request.batch_size_limit:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Batch size {len(request.events)} exceeds limit {request.batch_size_limit}"
                    )
                
                # Process batch
                result = self._processor.process_batch(
                    batch_data=request.events,
                    source_system=request.source_system
                )
                
                # Prepare invalid events details
                invalid_events = []
                for error in result.validation_errors:
                    invalid_events.append({
                        "event_id": error.get("event_id", "unknown"),
                        "errors": error.get("errors", ["Unknown error"]),
                        "error_type": "validation"
                    })
                
                # Get audit summary
                audit_summary = None
                if result.batch_id:
                    audit_summary = self._processor.get_batch_details(result.batch_id)
                
                # Schedule background processing if needed
                if result.success and len(result.processed_events) > 0:
                    background_tasks.add_task(
                        self._schedule_downstream_processing,
                        result.processed_events,
                        result.batch_id
                    )
                
                return BatchIngestionResponse(
                    success=result.success,
                    total_events=len(request.events),
                    processed_events=len(result.processed_events),
                    validation_errors=len(result.validation_errors),
                    processing_errors=len(result.processing_errors),
                    batch_id=result.batch_id,
                    processing_time_ms=result.processing_time_ms,
                    invalid_events=invalid_events,
                    audit_summary=audit_summary
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Batch ingestion failed: {str(e)}"
                )
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint"""
            try:
                audit_stats = self._processor.get_processing_statistics()
                return HealthResponse(
                    status="healthy",
                    timestamp=datetime.now(timezone.utc),
                    version="0.1.0",
                    audit_stats=audit_stats
                )
            except Exception as e:
                return HealthResponse(
                    status="unhealthy",
                    timestamp=datetime.now(timezone.utc),
                    version="0.1.0",
                    audit_stats={"error": str(e)}
                )
        
        @self.app.post("/audit/trail")
        async def get_audit_trail(request: AuditTrailRequest):
            """Get audit trail with filtering"""
            try:
                # Convert string enums to actual enums
                from src.utils.audit import AuditAction, AuditSeverity
                
                action = None
                if request.action:
                    try:
                        action = AuditAction(request.action)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid action: {request.action}"
                        )
                
                severity = None
                if request.severity:
                    try:
                        severity = AuditSeverity(request.severity)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid severity: {request.severity}"
                        )
                
                audit_records = self._processor.audit_logger.get_audit_trail(
                    event_id=request.event_id,
                    batch_id=request.batch_id,
                    action=action,
                    severity=severity,
                    limit=request.limit
                )
                
                return {
                    "audit_trail": [record.to_dict() for record in audit_records],
                    "total_records": len(audit_records),
                    "filters_applied": {
                        "event_id": request.event_id,
                        "batch_id": request.batch_id,
                        "action": request.action,
                        "severity": request.severity,
                        "limit": request.limit
                    }
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Audit trail retrieval failed: {str(e)}"
                )
        
        @self.app.get("/audit/event/{event_id}/lineage")
        async def get_event_lineage(event_id: str):
            """Get complete processing lineage for an event"""
            try:
                lineage = self._processor.get_event_lineage(event_id)
                return {
                    "event_id": event_id,
                    "lineage": lineage,
                    "total_records": len(lineage)
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Event lineage retrieval failed: {str(e)}"
                )
        
        @self.app.get("/audit/batch/{batch_id}")
        async def get_batch_details(batch_id: str):
            """Get detailed batch processing information"""
            try:
                batch_details = self._processor.get_batch_details(batch_id)
                return batch_details
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Batch details retrieval failed: {str(e)}"
                )
        
        @self.app.get("/stats")
        async def get_processing_statistics():
            """Get processing statistics"""
            try:
                stats = self._processor.get_processing_statistics()
                return stats
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Statistics retrieval failed: {str(e)}"
                )
        
        @self.app.get("/audit/export")
        async def export_audit_trail(format: str = "json"):
            """Export complete audit trail"""
            try:
                if format.lower() != "json":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unsupported format: {format}. Only 'json' is supported."
                    )
                
                export_data = self._processor.audit_logger.export_audit_trail(format)
                return JSONResponse(
                    content=export_data,
                    media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=audit_trail.json"}
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Audit export failed: {str(e)}"
                )
    
    async def _schedule_downstream_processing(self, events: List[BaseCanonicalEvent], batch_id: str):
        """Schedule downstream processing of events"""
        try:
            # This would integrate with downstream systems
            # For now, just log that processing was scheduled
            pass
        except Exception as e:
            # Log error but don't fail the ingestion
            pass
    
    def get_app(self) -> FastAPI:
        """Get FastAPI application instance"""
        return self.app


# Global API instance
def create_ingestion_api() -> FastAPI:
    """Create and configure ingestion API"""
    api = IngestionAPI()
    return api.get_app()


# For running directly
if __name__ == "__main__":
    import uvicorn
    app = create_ingestion_api()
    uvicorn.run(app, host="0.0.0.0", port=8000)
