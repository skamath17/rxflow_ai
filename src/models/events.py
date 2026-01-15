"""
Canonical Event Schemas for PharmIQ

This module defines the canonical event schemas that cover refill, PA, OOS, 
and bundle-relevant lifecycle events. All events are designed to be:
- Pseudonymized (no PHI)
- Deterministic 
- Audit-ready
- Bundle-aware
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class EventType(str, Enum):
    """Canonical event types for refill lifecycle"""
    REFILL_INITIATED = "refill_initiated"
    REFILL_ELIGIBLE = "refill_eligible"
    REFILL_BUNDLED = "refill_bundled"
    REFILL_SHIPPED = "refill_shipped"
    REFILL_CANCELLED = "refill_cancelled"
    REFILL_COMPLETED = "refill_completed"
    
    PA_SUBMITTED = "pa_submitted"
    PA_APPROVED = "pa_approved"
    PA_DENIED = "pa_denied"
    PA_EXPIRED = "pa_expired"
    
    OOS_DETECTED = "oos_detected"
    OOS_RESOLVED = "oos_resolved"
    
    BUNDLE_FORMED = "bundle_formed"
    BUNDLE_SPLIT = "bundle_split"
    BUNDLE_SHIPPED = "bundle_shipped"


class EventSource(str, Enum):
    """Source systems for canonical events"""
    CENTERSYNC = "centersync"
    HPIE = "hpie"
    HPC = "hpc"
    PA_SYSTEM = "pa_system"
    INVENTORY_SYSTEM = "inventory_system"
    MANUAL = "manual"


class RefillStatus(str, Enum):
    """Canonical refill status values"""
    PENDING = "pending"
    ELIGIBLE = "eligible"
    PROCESSING = "processing"
    BUNDLED = "bundled"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class PAStatus(str, Enum):
    """Canonical PA status values"""
    NOT_REQUIRED = "not_required"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    IN_REVIEW = "in_review"


class BaseCanonicalEvent(BaseModel):
    """Base class for all canonical events"""
    
    # Core identifiers (pseudonymized)
    event_id: str = Field(..., description="Unique event identifier")
    member_id: str = Field(..., description="Pseudonymized member identifier")
    refill_id: str = Field(..., description="Pseudonymized refill identifier")
    bundle_id: Optional[str] = Field(None, description="Pseudonymized bundle identifier")
    
    # Event metadata
    event_type: EventType = Field(..., description="Canonical event type")
    event_source: EventSource = Field(..., description="Source system")
    event_timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    received_timestamp: datetime = Field(..., description="Event receipt timestamp (UTC)")
    
    # Source system context
    source_event_id: Optional[str] = Field(None, description="Original event ID from source")
    source_system: Optional[str] = Field(None, description="Source system name")
    source_timestamp: Optional[datetime] = Field(None, description="Original timestamp from source")
    
    # Bundle context
    bundle_member_count: Optional[int] = Field(None, description="Number of members in bundle")
    bundle_refill_count: Optional[int] = Field(None, description="Number of refills in bundle")
    bundle_sequence: Optional[int] = Field(None, description="Sequence within bundle")
    
    # Audit and lineage
    correlation_id: Optional[str] = Field(None, description="Correlation ID for related events")
    causation_id: Optional[str] = Field(None, description="Causation ID for event chain")
    version: str = Field("1.0", description="Event schema version")
    
    @validator('event_timestamp', 'received_timestamp', 'source_timestamp')
    def validate_utc_timestamps(cls, v):
        """Ensure timestamps are in UTC"""
        if v and v.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware (UTC)")
        return v
    
    @validator('member_id', 'refill_id', 'bundle_id')
    def validate_pseudonymized_ids(cls, v):
        """Ensure identifiers are pseudonymized (basic validation)"""
        if v and len(v) < 8:
            raise ValueError("Pseudonymized IDs should be at least 8 characters")
        return v


class RefillEvent(BaseCanonicalEvent):
    """Canonical refill lifecycle event"""
    
    # Refill details
    drug_ndc: Optional[str] = Field(None, description="National Drug Code (pseudonymized if needed)")
    drug_name: Optional[str] = Field(None, description="Drug name (generic)")
    days_supply: Optional[int] = Field(None, description="Days supply")
    quantity: Optional[float] = Field(None, description="Prescription quantity")
    
    # Timing information
    refill_due_date: Optional[datetime] = Field(None, description="Refill due date")
    ship_by_date: Optional[datetime] = Field(None, description="Target ship date")
    last_fill_date: Optional[datetime] = Field(None, description="Last fill date")
    
    # Status information
    refill_status: Optional[RefillStatus] = Field(None, description="Canonical refill status")
    source_status: Optional[str] = Field(None, description="Original status from source")
    
    # Bundle timing metrics
    days_until_due: Optional[int] = Field(None, description="Days until refill due")
    days_since_last_fill: Optional[int] = Field(None, description="Days since last fill")
    bundle_alignment_score: Optional[float] = Field(None, description="Bundle alignment (0-1)")


class PAEvent(BaseCanonicalEvent):
    """Canonical Prior Authorization event"""
    
    # PA details
    pa_status: PAStatus = Field(..., description="Canonical PA status")
    pa_type: Optional[str] = Field(None, description="PA type (new, renewal, etc.)")
    pa_submitted_date: Optional[datetime] = Field(None, description="PA submission date")
    pa_response_date: Optional[datetime] = Field(None, description="PA response date")
    pa_expiry_date: Optional[datetime] = Field(None, description="PA expiry date")
    
    # PA timing metrics
    pa_processing_days: Optional[int] = Field(None, description="Days to PA decision")
    pa_validity_days: Optional[int] = Field(None, description="PA validity period")
    
    # PA context
    pa_reason_code: Optional[str] = Field(None, description="PA reason/diagnosis code")
    pa_outcome: Optional[str] = Field(None, description="PA outcome details")
    source_pa_id: Optional[str] = Field(None, description="Original PA ID")


class OSEvent(BaseCanonicalEvent):
    """Canonical Out-of-Stock event"""
    
    # OOS details
    oos_status: str = Field(..., description="OOS status (detected/resolved)")
    oos_reason: Optional[str] = Field(None, description="Reason for OOS")
    oos_detected_date: Optional[datetime] = Field(None, description="OOS detection date")
    oos_resolved_date: Optional[datetime] = Field(None, description="OOS resolution date")
    
    # OOS timing metrics
    oos_duration_days: Optional[int] = Field(None, description="Duration of OOS in days")
    estimated_resupply_date: Optional[datetime] = Field(None, description="Estimated resupply")
    
    # OOS context
    affected_quantity: Optional[float] = Field(None, description="Quantity affected")
    alternative_available: Optional[bool] = Field(None, description="Alternative available")
    source_oos_id: Optional[str] = Field(None, description="Original OOS ID")


class BundleEvent(BaseCanonicalEvent):
    """Canonical bundle lifecycle event"""
    
    # Bundle details
    bundle_type: Optional[str] = Field(None, description="Bundle type (standard, complex, etc.)")
    bundle_strategy: Optional[str] = Field(None, description="Bundling strategy used")
    bundle_formed_date: Optional[datetime] = Field(None, description="Bundle formation date")
    bundle_ship_date: Optional[datetime] = Field(None, description="Bundle ship date")
    
    # Bundle composition
    member_refills: List[Dict[str, Any]] = Field(default_factory=list, description="Member refills in bundle")
    total_refills: int = Field(..., description="Total refills in bundle")
    total_members: int = Field(..., description="Total members in bundle")
    
    # Bundle metrics
    bundle_efficiency_score: Optional[float] = Field(None, description="Bundle efficiency (0-1)")
    bundle_complexity_score: Optional[float] = Field(None, description="Bundle complexity (0-1)")
    split_risk_score: Optional[float] = Field(None, description="Bundle split risk (0-1)")


# Event factory for creating appropriate event types
def create_canonical_event(event_data: Dict[str, Any]) -> BaseCanonicalEvent:
    """Factory function to create appropriate canonical event type"""
    event_type = event_data.get("event_type")
    
    if event_type in [EventType.PA_SUBMITTED, EventType.PA_APPROVED, EventType.PA_DENIED, EventType.PA_EXPIRED]:
        return PAEvent(**event_data)
    elif event_type in [EventType.OOS_DETECTED, EventType.OOS_RESOLVED]:
        return OSEvent(**event_data)
    elif event_type in [EventType.BUNDLE_FORMED, EventType.BUNDLE_SPLIT, EventType.BUNDLE_SHIPPED]:
        return BundleEvent(**event_data)
    else:
        return RefillEvent(**event_data)
