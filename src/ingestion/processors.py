"""
Event Processing for PharmIQ

Core event processing logic with validation and audit logging.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

from src.models.events import BaseCanonicalEvent, create_canonical_event
from src.utils.validation import EventValidator, ValidationResult
from src.utils.audit import AuditLogger, AuditAction


@dataclass
class ProcessingResult:
    """Result of event processing"""
    success: bool
    processed_events: List[BaseCanonicalEvent]
    validation_errors: List[Dict[str, Any]]
    processing_errors: List[Dict[str, Any]]
    processing_time_ms: int
    batch_id: Optional[str] = None


class EventProcessor:
    """Core event processing with validation and audit logging"""
    
    def __init__(self, audit_logger: AuditLogger = None):
        self.audit_logger = audit_logger or AuditLogger()
        self.validator = EventValidator()
    
    def process_single_event(self, event_data: Dict[str, Any], 
                           source_system: str = None) -> ProcessingResult:
        """Process a single event"""
        start_time = time.time()
        event_id = event_data.get("event_id", "unknown")
        
        try:
            # Log event receipt
            self.audit_logger.log_event_received(
                event_id=event_id,
                source_system=source_system or "unknown",
                event_data=event_data
            )
            
            # Validate event
            validation_result = self.validator.validate_single_event(event_data)
            self.audit_logger.log_event_validated(
                event_id=event_id,
                validation_result=validation_result.is_valid,
                errors=validation_result.errors if not validation_result.is_valid else None
            )
            
            if not validation_result.is_valid:
                processing_time_ms = int((time.time() - start_time) * 1000)
                return ProcessingResult(
                    success=False,
                    processed_events=[],
                    validation_errors=[{"event_id": event_id, "errors": validation_result.errors}],
                    processing_errors=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Create canonical event
            canonical_event = create_canonical_event(event_data)
            
            # Add received timestamp if not present
            if not canonical_event.received_timestamp:
                canonical_event.received_timestamp = datetime.now(timezone.utc)
            
            # Log successful processing
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.audit_logger.log_event_processed(
                event_id=event_id,
                processing_time_ms=processing_time_ms,
                outcome="canonical_event_created"
            )
            
            return ProcessingResult(
                success=True,
                processed_events=[canonical_event],
                validation_errors=[],
                processing_errors=[],
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.audit_logger.log_processing_error(
                event_id=event_id,
                batch_id=None,
                error=e,
                processing_time_ms=processing_time_ms
            )
            
            return ProcessingResult(
                success=False,
                processed_events=[],
                validation_errors=[],
                processing_errors=[{"event_id": event_id, "error": str(e)}],
                processing_time_ms=processing_time_ms
            )
    
    def process_batch(self, batch_data: List[Dict[str, Any]], 
                      source_system: str = None) -> ProcessingResult:
        """Process a batch of events"""
        start_time = time.time()
        batch_id = self.audit_logger.generate_batch_id()
        
        try:
            # Log batch receipt
            self.audit_logger.log_batch_received(
                batch_id=batch_id,
                source_system=source_system or "unknown",
                event_count=len(batch_data)
            )
            
            # Validate batch
            batch_validation, event_validations = self.validator.validate_batch(batch_data)
            self.audit_logger.log_batch_validated(
                batch_id=batch_id,
                valid_count=len([ev for ev in event_validations if ev[1].is_valid]),
                invalid_count=len([ev for ev in event_validations if not ev[1].is_valid])
            )
            
            # If batch validation failed, return early
            if not batch_validation.is_valid:
                processing_time_ms = int((time.time() - start_time) * 1000)
                return ProcessingResult(
                    success=False,
                    processed_events=[],
                    validation_errors=[{"batch_error": error} for error in batch_validation.errors],
                    processing_errors=[],
                    processing_time_ms=processing_time_ms,
                    batch_id=batch_id
                )
            
            # Process events
            processed_events = []
            validation_errors = []
            processing_errors = []
            
            for i, event_data in enumerate(batch_data):
                event_id = event_data.get("event_id", f"event_{i}")
                
                # Skip events that failed validation
                if i < len(event_validations) and not event_validations[i][1].is_valid:
                    validation_errors.append({
                        "event_id": event_id,
                        "errors": event_validations[i][1].errors,
                        "warnings": event_validations[i][1].warnings
                    })
                    continue
                
                try:
                    # Create canonical event
                    canonical_event = create_canonical_event(event_data)
                    
                    # Add received timestamp if not present
                    if not canonical_event.received_timestamp:
                        canonical_event.received_timestamp = datetime.now(timezone.utc)
                    
                    # Add batch context
                    canonical_event.correlation_id = batch_id
                    
                    processed_events.append(canonical_event)
                    
                except Exception as e:
                    processing_errors.append({"event_id": event_id, "error": str(e)})
                    self.audit_logger.log_processing_error(
                        event_id=event_id,
                        batch_id=batch_id,
                        error=e,
                        processing_time_ms=0
                    )
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Log batch completion
            self.audit_logger.log_batch_processed(
                batch_id=batch_id,
                processing_time_ms=processing_time_ms,
                processed_count=len(processed_events)
            )
            
            # Determine success
            success = len(processing_errors) == 0 and len(validation_errors) == 0
            
            return ProcessingResult(
                success=success,
                processed_events=processed_events,
                validation_errors=validation_errors,
                processing_errors=processing_errors,
                processing_time_ms=processing_time_ms,
                batch_id=batch_id
            )
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.audit_logger.log_processing_error(
                event_id=None,
                batch_id=batch_id,
                error=e,
                processing_time_ms=processing_time_ms
            )
            
            return ProcessingResult(
                success=False,
                processed_events=[],
                validation_errors=[],
                processing_errors=[{"batch_id": batch_id, "error": str(e)}],
                processing_time_ms=processing_time_ms,
                batch_id=batch_id
            )
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics from audit log"""
        audit_stats = self.audit_logger.get_audit_statistics()
        
        # Add processing-specific statistics
        processed_events = len(self.audit_logger.get_audit_trail(action=AuditAction.EVENT_PROCESSED))
        failed_validations = len(self.audit_logger.get_audit_trail(action=AuditAction.VALIDATION_FAILED))
        failed_processing = len(self.audit_logger.get_audit_trail(action=AuditAction.PROCESSING_FAILED))
        
        return {
            **audit_stats,
            "processed_events": processed_events,
            "failed_validations": failed_validations,
            "failed_processing": failed_processing,
            "success_rate": processed_events / (processed_events + failed_processing) if (processed_events + failed_processing) > 0 else 0
        }
    
    def get_event_lineage(self, event_id: str) -> List[Dict[str, Any]]:
        """Get complete processing lineage for an event"""
        lineage_records = self.audit_logger.get_event_lineage(event_id)
        return [record.to_dict() for record in lineage_records]
    
    def get_batch_details(self, batch_id: str) -> Dict[str, Any]:
        """Get detailed batch processing information"""
        return self.audit_logger.get_batch_summary(batch_id)


class EventEnricher:
    """Event enrichment for additional context and metrics"""
    
    def __init__(self):
        pass
    
    def enrich_event(self, event: BaseCanonicalEvent) -> BaseCanonicalEvent:
        """Enrich event with additional context"""
        # Add enrichment logic here
        # For now, return the event as-is
        return event
    
    def enrich_batch(self, events: List[BaseCanonicalEvent]) -> List[BaseCanonicalEvent]:
        """Enrich a batch of events"""
        return [self.enrich_event(event) for event in events]


class EventRouter:
    """Route events to appropriate downstream systems"""
    
    def __init__(self):
        self.routes = {}
    
    def add_route(self, event_type: str, destination: str) -> None:
        """Add routing rule for event type"""
        self.routes[event_type] = destination
    
    def route_event(self, event: BaseCanonicalEvent) -> List[str]:
        """Get routing destinations for event"""
        event_type = event.event_type.value
        destinations = []
        
        # Direct route match
        if event_type in self.routes:
            destinations.append(self.routes[event_type])
        
        # Category-based routing
        if event_type.startswith("refill_"):
            destinations.append("refill_processor")
        elif event_type.startswith("pa_"):
            destinations.append("pa_processor")
        elif event_type.startswith("oos_"):
            destinations.append("oos_processor")
        elif event_type.startswith("bundle_"):
            destinations.append("bundle_processor")
        
        # Default route
        if not destinations:
            destinations.append("default_processor")
        
        return destinations
    
    def route_batch(self, events: List[BaseCanonicalEvent]) -> Dict[str, List[BaseCanonicalEvent]]:
        """Route batch of events by destination"""
        routed_events = {}
        
        for event in events:
            destinations = self.route_event(event)
            for destination in destinations:
                if destination not in routed_events:
                    routed_events[destination] = []
                routed_events[destination].append(event)
        
        return routed_events
