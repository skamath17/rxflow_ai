"""
Event Validation for PharmIQ

Comprehensive validation for canonical events and batches.
"""

from datetime import datetime, timezone
import re
from typing import Dict, Any, List, Tuple, Optional
from pydantic import ValidationError

from src.models.events import BaseCanonicalEvent, create_canonical_event


class ValidationResult:
    """Validation result with errors and warnings"""
    
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str) -> None:
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add validation warning"""
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge with another validation result"""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings
        )


class EventValidator:
    """Comprehensive event validation"""
    
    def __init__(self):
        self.required_fields = {
            "event_id",
            "member_id", 
            "refill_id",
            "event_type",
            "event_source",
            "event_timestamp",
            "received_timestamp"
        }
        self.phi_denylist_fields = {
            "first_name",
            "last_name",
            "full_name",
            "member_name",
            "patient_name",
            "dob",
            "date_of_birth",
            "birth_date",
            "email",
            "phone",
            "phone_number",
            "address",
            "street_address",
            "city",
            "state",
            "zip",
            "postal_code",
            "ssn",
            "social_security_number",
            "medical_record_number",
            "mrn",
        }
    
    def validate_single_event(self, event_data: Dict[str, Any]) -> ValidationResult:
        """Validate a single canonical event"""
        result = ValidationResult(is_valid=True)
        
        # Check required fields
        missing_fields = self.required_fields - set(event_data.keys())
        if missing_fields:
            result.add_error(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate field formats
        self._validate_identifiers(event_data, result)
        self._validate_phi_denylist(event_data, result)
        self._validate_timestamps(event_data, result)
        self._validate_event_structure(event_data, result)
        
        # Try to create canonical event for full validation
        if result.is_valid:
            try:
                canonical_event = create_canonical_event(event_data)
                self._validate_event_specific_fields(canonical_event, result)
            except ValidationError as e:
                result.add_error(f"Pydantic validation failed: {str(e)}")
            except Exception as e:
                result.add_error(f"Event creation failed: {str(e)}")
        
        return result
    
    def validate_batch(self, batch_data: List[Dict[str, Any]]) -> Tuple[ValidationResult, List[Tuple[int, ValidationResult]]]:
        """Validate a batch of events"""
        batch_result = ValidationResult(is_valid=True)
        event_results = []
        
        # Batch-level validation
        if not batch_data:
            batch_result.add_error("Batch is empty")
            return batch_result, event_results
        
        if len(batch_data) > 10000:  # Configurable batch size limit
            batch_result.add_warning(f"Large batch size: {len(batch_data)} events")
        
        # Validate each event
        for i, event_data in enumerate(batch_data):
            event_result = self.validate_single_event(event_data)
            event_results.append((i, event_result))
            
            if not event_result.is_valid:
                batch_result.add_warning(f"Event {i} validation failed: {'; '.join(event_result.errors)}")
        
        # Check for duplicate event IDs
        event_ids = [event.get("event_id") for event in batch_data if event.get("event_id")]
        duplicate_ids = set([eid for eid in event_ids if event_ids.count(eid) > 1])
        if duplicate_ids:
            batch_result.add_error(f"Duplicate event IDs found: {', '.join(duplicate_ids)}")
        
        return batch_result, event_results
    
    def _validate_identifiers(self, event_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate identifier fields"""
        id_fields = ["event_id", "member_id", "refill_id"]
        
        for field in id_fields:
            if field in event_data:
                value = event_data[field]
                if not isinstance(value, str) or len(value) < 8:
                    result.add_error(f"{field} must be a string of at least 8 characters")
                if not self._is_pseudonymous_id(value):
                    result.add_error(f"{field} must be a pseudonymized identifier")
        
        # Optional bundle_id validation
        if "bundle_id" in event_data and event_data["bundle_id"]:
            bundle_id = event_data["bundle_id"]
            if not isinstance(bundle_id, str) or len(bundle_id) < 8:
                result.add_error("bundle_id must be a string of at least 8 characters")
            if not self._is_pseudonymous_id(bundle_id):
                result.add_error("bundle_id must be a pseudonymized identifier")

        member_refills = event_data.get("member_refills") or []
        if isinstance(member_refills, list):
            for idx, member_refill in enumerate(member_refills):
                if not isinstance(member_refill, dict):
                    result.add_error(f"member_refills[{idx}] must be an object")
                    continue
                for field in ("member_id", "refill_id"):
                    value = member_refill.get(field)
                    if value is None:
                        continue
                    if not isinstance(value, str) or len(value) < 8:
                        result.add_error(f"member_refills[{idx}].{field} must be a string of at least 8 characters")
                    elif not self._is_pseudonymous_id(value):
                        result.add_error(f"member_refills[{idx}].{field} must be a pseudonymized identifier")

    @staticmethod
    def _is_pseudonymous_id(value: str) -> bool:
        if not value:
            return False
        if "@" in value:
            return False
        if re.search(r"\b\d{3}-\d{2}-\d{4}\b", value):
            return False
        if re.search(r"\b\+?\d{10,15}\b", value.replace("-", "")):
            return False
        return re.fullmatch(r"[A-Za-z0-9_-]{8,}", value) is not None

    def _validate_phi_denylist(self, event_data: Dict[str, Any], result: ValidationResult) -> None:
        for field in self.phi_denylist_fields:
            if field in event_data and event_data[field] not in (None, ""):
                result.add_error(f"PHI field not allowed: {field}")
    
    def _validate_timestamps(self, event_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate timestamp fields"""
        timestamp_fields = ["event_timestamp", "received_timestamp", "source_timestamp"]
        
        for field in timestamp_fields:
            if field in event_data and event_data[field] is not None:
                timestamp = event_data[field]
                
                # Handle both datetime objects and ISO strings
                if isinstance(timestamp, str):
                    try:
                        from datetime import datetime
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        result.add_error(f"{field} must be a valid ISO datetime string")
                        continue
                elif not isinstance(timestamp, datetime):
                    result.add_error(f"{field} must be a datetime object or ISO string")
                    continue
                
                if timestamp.tzinfo is None:
                    result.add_error(f"{field} must be timezone-aware (UTC)")
                elif timestamp.tzinfo != timezone.utc:
                    result.add_warning(f"{field} is not in UTC timezone")
        
        # Validate timestamp ordering
        ts_fields = ["event_timestamp", "received_timestamp"]
        if all(field in event_data for field in ts_fields):
            event_ts = event_data["event_timestamp"]
            received_ts = event_data["received_timestamp"]
            
            # Convert to datetime objects if they are strings
            if isinstance(event_ts, str):
                try:
                    event_ts = datetime.fromisoformat(event_ts.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return
            if isinstance(received_ts, str):
                try:
                    received_ts = datetime.fromisoformat(received_ts.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return
            
            if isinstance(event_ts, datetime) and isinstance(received_ts, datetime):
                if received_ts < event_ts:
                    result.add_warning("received_timestamp is earlier than event_timestamp")
                # Check for excessive delay
                delay_hours = (received_ts - event_ts).total_seconds() / 3600
                if delay_hours > 24:
                    result.add_warning(f"High processing delay: {delay_hours:.1f} hours")
    
    def _validate_event_structure(self, event_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate event structure and consistency"""
        event_type = event_data.get("event_type")
        event_source = event_data.get("event_source")
        
        # Validate event type
        if event_type:
            valid_types = [
                "refill_initiated", "refill_eligible", "refill_bundled", "refill_shipped", 
                "refill_cancelled", "refill_completed", "pa_submitted", "pa_approved", 
                "pa_denied", "pa_expired", "oos_detected", "oos_resolved", 
                "bundle_formed", "bundle_split", "bundle_shipped"
            ]
            if event_type not in valid_types:
                result.add_error(f"Invalid event_type: {event_type}")
        
        # Validate event source
        if event_source:
            valid_sources = ["centersync", "hpie", "hpc", "pa_system", "inventory_system", "manual"]
            if event_source not in valid_sources:
                result.add_error(f"Invalid event_source: {event_source}")
        
        # Validate bundle context consistency
        bundle_id = event_data.get("bundle_id")
        bundle_member_count = event_data.get("bundle_member_count")
        bundle_refill_count = event_data.get("bundle_refill_count")
        
        if bundle_id:
            if bundle_member_count is None:
                result.add_warning("bundle_id present but bundle_member_count missing")
            if bundle_refill_count is None:
                result.add_warning("bundle_id present but bundle_refill_count missing")
        elif bundle_member_count or bundle_refill_count:
            result.add_warning("Bundle metrics present but bundle_id missing")
        
        # Validate numeric fields
        numeric_fields = ["bundle_member_count", "bundle_refill_count", "bundle_sequence", 
                         "days_supply", "quantity", "days_until_due", "days_since_last_fill",
                         "pa_processing_days", "pa_validity_days", "oos_duration_days"]
        
        for field in numeric_fields:
            if field in event_data and event_data[field] is not None:
                value = event_data[field]
                if not isinstance(value, (int, float)) or value < 0:
                    result.add_error(f"{field} must be a non-negative number")
                if isinstance(value, float) and not value.is_integer() and field.endswith("_count"):
                    result.add_error(f"{field} must be an integer")
        
        # Validate score fields (0-1 range)
        score_fields = ["bundle_alignment_score", "bundle_efficiency_score", 
                       "bundle_complexity_score", "split_risk_score"]
        
        for field in score_fields:
            if field in event_data and event_data[field] is not None:
                value = event_data[field]
                if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                    result.add_error(f"{field} must be between 0 and 1")
    
    def _validate_event_specific_fields(self, event: BaseCanonicalEvent, result: ValidationResult) -> None:
        """Validate event-type specific fields"""
        event_type = event.event_type.value
        
        # PA event specific validation
        if event_type.startswith("pa_"):
            if not hasattr(event, 'pa_status'):
                result.add_error("PA events must have pa_status field")
        
        # OOS event specific validation
        if event_type.startswith("oos_"):
            if not hasattr(event, 'oos_status'):
                result.add_error("OOS events must have oos_status field")
        
        # Bundle event specific validation
        if event_type.startswith("bundle_"):
            if not hasattr(event, 'total_refills') or not hasattr(event, 'total_members'):
                result.add_error("Bundle events must have total_refills and total_members fields")
            if hasattr(event, 'total_refills') and hasattr(event, 'total_members'):
                if event.total_refills <= 0 or event.total_members <= 0:
                    result.add_error("Bundle totals must be positive")
                if event.total_refills < event.total_members:
                    result.add_warning("More members than refills in bundle")
        
        # Refill event specific validation
        if event_type.startswith("refill_"):
            if hasattr(event, 'days_supply') and event.days_supply and event.days_supply > 365:
                result.add_warning("days_supply exceeds 365 days")
            if hasattr(event, 'quantity') and event.quantity and event.quantity > 1000:
                result.add_warning("quantity exceeds 1000 units")


class BatchValidator:
    """Batch-level validation and processing"""
    
    def __init__(self, event_validator: EventValidator = None):
        self.event_validator = event_validator or EventValidator()
    
    def validate_and_prepare_batch(self, batch_data: List[Dict[str, Any]], 
                                  source_system: str) -> Tuple[ValidationResult, List[Dict[str, Any]]]:
        """Validate batch and prepare for processing"""
        batch_result, event_results = self.event_validator.validate_batch(batch_data)
        
        # Separate valid and invalid events
        valid_events = []
        invalid_events = []
        
        for i, (event_idx, event_result) in enumerate(event_results):
            if event_result.is_valid:
                valid_events.append(batch_data[event_idx])
            else:
                invalid_events.append({
                    "index": event_idx,
                    "event_data": batch_data[event_idx],
                    "validation_errors": event_result.errors,
                    "validation_warnings": event_result.warnings
                })
        
        # Add batch summary to result
        batch_result.details = {
            "total_events": len(batch_data),
            "valid_events": len(valid_events),
            "invalid_events": len(invalid_events),
            "source_system": source_system,
            "invalid_event_details": invalid_events
        }
        
        return batch_result, valid_events
