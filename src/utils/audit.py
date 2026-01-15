"""
Immutable Audit Logging for PharmIQ

Provides comprehensive audit trail for all event processing operations.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel


class AuditAction(str, Enum):
    """Audit action types"""
    EVENT_RECEIVED = "event_received"
    EVENT_VALIDATED = "event_validated"
    EVENT_PROCESSED = "event_processed"
    BATCH_RECEIVED = "batch_received"
    BATCH_VALIDATED = "batch_validated"
    BATCH_PROCESSED = "batch_processed"
    VALIDATION_FAILED = "validation_failed"
    PROCESSING_FAILED = "processing_failed"


class AuditSeverity(str, Enum):
    """Audit severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditRecord(BaseModel):
    """Individual audit record"""
    audit_id: str
    timestamp: datetime
    action: AuditAction
    severity: AuditSeverity
    event_id: Optional[str] = None
    batch_id: Optional[str] = None
    source_system: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            **self.dict(),
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "severity": self.severity.value
        }


class AuditLogger:
    """Immutable audit logger for PharmIQ events"""
    
    def __init__(self):
        self._audit_trail: List[AuditRecord] = []
        self._batch_counter = 0
        self._event_counter = 0
    
    def generate_audit_id(self, prefix: str = "audit") -> str:
        """Generate unique audit ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        counter = self._event_counter if prefix == "audit" else self._batch_counter
        self._event_counter += 1
        return f"{prefix}_{timestamp}_{counter:06d}"
    
    def generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        self._batch_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"batch_{timestamp}_{self._batch_counter:06d}"
    
    def log_event_received(self, event_id: str, source_system: str, event_data: Dict[str, Any]) -> AuditRecord:
        """Log event receipt"""
        audit_id = self.generate_audit_id("recv")
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.EVENT_RECEIVED,
            severity=AuditSeverity.INFO,
            event_id=event_id,
            source_system=source_system,
            message=f"Event received from {source_system}",
            details={"event_type": event_data.get("event_type"), "event_size": len(str(event_data))}
        )
        self._audit_trail.append(record)
        return record
    
    def log_event_validated(self, event_id: str, validation_result: bool, errors: Optional[List[str]] = None) -> AuditRecord:
        """Log event validation result"""
        audit_id = self.generate_audit_id("val")
        severity = AuditSeverity.INFO if validation_result else AuditSeverity.ERROR
        action = AuditAction.EVENT_VALIDATED if validation_result else AuditAction.VALIDATION_FAILED
        
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=action,
            severity=severity,
            event_id=event_id,
            message=f"Event validation {'passed' if validation_result else 'failed'}",
            details={"validation_errors": errors} if errors else None
        )
        self._audit_trail.append(record)
        return record
    
    def log_event_processed(self, event_id: str, processing_time_ms: int, outcome: str) -> AuditRecord:
        """Log successful event processing"""
        audit_id = self.generate_audit_id("proc")
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.EVENT_PROCESSED,
            severity=AuditSeverity.INFO,
            event_id=event_id,
            message=f"Event processed successfully",
            details={"outcome": outcome, "processing_time_ms": processing_time_ms},
            processing_time_ms=processing_time_ms
        )
        self._audit_trail.append(record)
        return record
    
    def log_batch_received(self, batch_id: str, source_system: str, event_count: int) -> AuditRecord:
        """Log batch receipt"""
        audit_id = self.generate_audit_id("batch")
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.BATCH_RECEIVED,
            severity=AuditSeverity.INFO,
            batch_id=batch_id,
            source_system=source_system,
            message=f"Batch received with {event_count} events",
            details={"event_count": event_count}
        )
        self._audit_trail.append(record)
        return record
    
    def log_batch_validated(self, batch_id: str, valid_count: int, invalid_count: int) -> AuditRecord:
        """Log batch validation results"""
        audit_id = self.generate_audit_id("bval")
        severity = AuditSeverity.WARNING if invalid_count > 0 else AuditSeverity.INFO
        
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.BATCH_VALIDATED,
            severity=severity,
            batch_id=batch_id,
            message=f"Batch validation: {valid_count} valid, {invalid_count} invalid",
            details={"valid_count": valid_count, "invalid_count": invalid_count}
        )
        self._audit_trail.append(record)
        return record
    
    def log_batch_processed(self, batch_id: str, processing_time_ms: int, processed_count: int) -> AuditRecord:
        """Log successful batch processing"""
        audit_id = self.generate_audit_id("bproc")
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.BATCH_PROCESSED,
            severity=AuditSeverity.INFO,
            batch_id=batch_id,
            message=f"Batch processed: {processed_count} events",
            details={"processed_count": processed_count, "processing_time_ms": processing_time_ms},
            processing_time_ms=processing_time_ms
        )
        self._audit_trail.append(record)
        return record
    
    def log_processing_error(self, event_id: Optional[str], batch_id: Optional[str], error: Exception, processing_time_ms: int) -> AuditRecord:
        """Log processing error"""
        audit_id = self.generate_audit_id("err")
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.PROCESSING_FAILED,
            severity=AuditSeverity.ERROR,
            event_id=event_id,
            batch_id=batch_id,
            message=f"Processing failed: {str(error)}",
            details={"error_type": type(error).__name__},
            error_code=type(error).__name__,
            stack_trace=str(error.__traceback__) if error.__traceback__ else None,
            processing_time_ms=processing_time_ms
        )
        self._audit_trail.append(record)
        return record
    
    def get_audit_trail(self, 
                       event_id: Optional[str] = None,
                       batch_id: Optional[str] = None,
                       action: Optional[AuditAction] = None,
                       severity: Optional[AuditSeverity] = None,
                       limit: Optional[int] = None) -> List[AuditRecord]:
        """Get filtered audit trail"""
        filtered_trail = self._audit_trail
        
        if event_id:
            filtered_trail = [r for r in filtered_trail if r.event_id == event_id]
        if batch_id:
            filtered_trail = [r for r in filtered_trail if r.batch_id == batch_id]
        if action:
            filtered_trail = [r for r in filtered_trail if r.action == action]
        if severity:
            filtered_trail = [r for r in filtered_trail if r.severity == severity]
        
        if limit:
            filtered_trail = filtered_trail[-limit:]
        
        return filtered_trail
    
    def get_event_lineage(self, event_id: str) -> List[AuditRecord]:
        """Get complete audit lineage for a specific event"""
        return [r for r in self._audit_trail if r.event_id == event_id]
    
    def get_batch_summary(self, batch_id: str) -> Dict[str, Any]:
        """Get batch processing summary"""
        batch_records = [r for r in self._audit_trail if r.batch_id == batch_id]
        
        if not batch_records:
            return {"error": "Batch not found"}
        
        summary = {
            "batch_id": batch_id,
            "actions": [r.action.value for r in batch_records],
            "total_records": len(batch_records),
            "errors": len([r for r in batch_records if r.severity == AuditSeverity.ERROR]),
            "warnings": len([r for r in batch_records if r.severity == AuditSeverity.WARNING]),
            "start_time": min(r.timestamp for r in batch_records).isoformat(),
            "end_time": max(r.timestamp for r in batch_records).isoformat(),
            "total_processing_time_ms": sum(r.processing_time_ms or 0 for r in batch_records)
        }
        
        return summary
    
    def export_audit_trail(self, format: str = "json") -> str:
        """Export audit trail in specified format"""
        if format.lower() == "json":
            return json.dumps([record.to_dict() for record in self._audit_trail], indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def clear_audit_trail(self) -> None:
        """Clear audit trail (for testing only)"""
        self._audit_trail.clear()
        self._batch_counter = 0
        self._event_counter = 0
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics"""
        total_records = len(self._audit_trail)
        if total_records == 0:
            return {"total_records": 0}
        
        error_count = len([r for r in self._audit_trail if r.severity == AuditSeverity.ERROR])
        warning_count = len([r for r in self._audit_trail if r.severity == AuditSeverity.WARNING])
        
        action_counts = {}
        for record in self._audit_trail:
            action_counts[record.action.value] = action_counts.get(record.action.value, 0) + 1
        
        avg_processing_time = sum(r.processing_time_ms or 0 for r in self._audit_trail) / total_records
        
        return {
            "total_records": total_records,
            "error_count": error_count,
            "warning_count": warning_count,
            "error_rate": error_count / total_records,
            "warning_rate": warning_count / total_records,
            "action_counts": action_counts,
            "average_processing_time_ms": avg_processing_time,
            "batches_processed": len(set(r.batch_id for r in self._audit_trail if r.batch_id)),
            "events_processed": len(set(r.event_id for r in self._audit_trail if r.event_id))
        }
