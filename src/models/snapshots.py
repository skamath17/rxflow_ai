"""
Refill Snapshot Models for PharmIQ

This module defines the snapshot aggregation models that capture the current
state of refills by aggregating canonical events. Snapshots provide a
time-bounded view of refill lifecycle state for risk analysis.

Snapshots are designed to be:
- Event-driven (aggregated from canonical events)
- Time-bounded (capture state at specific point in time)
- Bundle-aware (include bundle context and timing)
- Risk-ready (include metrics needed for risk scoring)
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator

from .events import RefillStatus, PAStatus, EventType


class SnapshotStage(str, Enum):
    """Refill lifecycle stages for snapshot classification"""
    INITIATED = "initiated"
    ELIGIBLE = "eligible"
    PA_PENDING = "pa_pending"
    PA_APPROVED = "pa_approved"
    PA_DENIED = "pa_denied"
    BUNDLED = "bundled"
    OOS_DETECTED = "oos_detected"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PAState(str, Enum):
    """PA state within snapshot"""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class BundleTimingState(str, Enum):
    """Bundle timing alignment state"""
    ALIGNED = "aligned"
    EARLY = "early"
    LATE = "late"
    MISALIGNED = "misaligned"
    UNKNOWN = "unknown"


class RefillSnapshot(BaseModel):
    """Aggregated snapshot of a refill's current state"""
    
    # Core identifiers
    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    member_id: str = Field(..., description="Pseudonymized member identifier")
    refill_id: str = Field(..., description="Pseudonymized refill identifier")
    bundle_id: Optional[str] = Field(None, description="Pseudonymized bundle identifier")
    
    # Snapshot metadata
    snapshot_timestamp: datetime = Field(..., description="Snapshot creation timestamp (UTC)")
    snapshot_version: str = Field("1.0", description="Snapshot schema version")
    
    # Current stage and state
    current_stage: SnapshotStage = Field(..., description="Current refill lifecycle stage")
    pa_state: PAState = Field(..., description="Current PA state")
    bundle_timing_state: BundleTimingState = Field(..., description="Bundle timing alignment")
    
    # Refill details (latest known)
    drug_ndc: Optional[str] = Field(None, description="National Drug Code")
    drug_name: Optional[str] = Field(None, description="Drug name")
    days_supply: Optional[int] = Field(None, description="Days supply")
    quantity: Optional[float] = Field(None, description="Prescription quantity")
    
    # Timing information
    refill_due_date: Optional[datetime] = Field(None, description="Refill due date")
    ship_by_date: Optional[datetime] = Field(None, description="Target ship date")
    last_fill_date: Optional[datetime] = Field(None, description="Last fill date")
    
    # Status information
    refill_status: Optional[RefillStatus] = Field(None, description="Canonical refill status")
    source_status: Optional[str] = Field(None, description="Original status from source")
    
    # Bundle context
    bundle_member_count: Optional[int] = Field(None, description="Number of members in bundle")
    bundle_refill_count: Optional[int] = Field(None, description="Number of refills in bundle")
    bundle_sequence: Optional[int] = Field(None, description="Sequence within bundle")
    bundle_alignment_score: Optional[float] = Field(None, description="Bundle alignment (0-1)")
    
    # Event aggregation metrics
    total_events: int = Field(..., description="Total events aggregated")
    latest_event_timestamp: datetime = Field(..., description="Timestamp of latest event")
    earliest_event_timestamp: datetime = Field(..., description="Timestamp of earliest event")
    
    # Event type counts
    refill_events: int = Field(0, description="Number of refill events")
    pa_events: int = Field(0, description="Number of PA events")
    oos_events: int = Field(0, description="Number of OOS events")
    bundle_events: int = Field(0, description="Number of bundle events")
    
    # Key event timestamps
    initiated_timestamp: Optional[datetime] = Field(None, description="Refill initiation timestamp")
    eligible_timestamp: Optional[datetime] = Field(None, description="Eligibility determination timestamp")
    pa_submitted_timestamp: Optional[datetime] = Field(None, description="PA submission timestamp")
    pa_resolved_timestamp: Optional[datetime] = Field(None, description="PA resolution timestamp")
    bundled_timestamp: Optional[datetime] = Field(None, description="Bundle formation timestamp")
    shipped_timestamp: Optional[datetime] = Field(None, description="Shipment timestamp")
    completed_timestamp: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # PA-specific information
    pa_type: Optional[str] = Field(None, description="PA type")
    pa_processing_days: Optional[int] = Field(None, description="Days to PA decision")
    pa_expiry_date: Optional[datetime] = Field(None, description="PA expiry date")
    
    # OOS-specific information
    oos_detected_timestamp: Optional[datetime] = Field(None, description="OOS detection timestamp")
    oos_resolved_timestamp: Optional[datetime] = Field(None, description="OOS resolution timestamp")
    
    # Timing metrics (computed)
    days_until_due: Optional[int] = Field(None, description="Days until refill due")
    days_since_last_fill: Optional[int] = Field(None, description="Days since last fill")
    days_in_current_stage: Optional[int] = Field(None, description="Days in current lifecycle stage")
    total_processing_days: Optional[int] = Field(None, description="Total days since initiation")
    
    # Event lineage
    event_ids: List[str] = Field(default_factory=list, description="Aggregated event IDs")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for related events")
    
    @validator('snapshot_timestamp', 'latest_event_timestamp', 'earliest_event_timestamp')
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
    
    @validator('bundle_alignment_score')
    def validate_alignment_score(cls, v):
        """Ensure alignment score is between 0 and 1"""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Bundle alignment score must be between 0 and 1")
        return v


class SnapshotMetadata(BaseModel):
    """Metadata for snapshot aggregation process"""
    
    snapshot_id: str = Field(..., description="Snapshot identifier")
    aggregation_timestamp: datetime = Field(..., description="Aggregation completion timestamp")
    source_events_count: int = Field(..., description="Number of source events aggregated")
    aggregation_version: str = Field("1.0", description="Aggregation algorithm version")
    
    # Processing metrics
    aggregation_time_ms: int = Field(..., description="Time to aggregate snapshot (milliseconds)")
    events_processed: int = Field(..., description="Total events processed")
    events_filtered: int = Field(0, description="Events filtered out during aggregation")
    
    # Data quality indicators
    missing_required_fields: List[str] = Field(default_factory=list, description="Missing required fields")
    data_quality_score: float = Field(1.0, description="Data quality score (0-1)")
    
    # System context
    processor_version: str = Field(..., description="Snapshot processor version")
    source_systems: List[str] = Field(default_factory=list, description="Source systems contributing events")


class SnapshotQuery(BaseModel):
    """Query parameters for snapshot retrieval"""
    
    member_id: Optional[str] = Field(None, description="Filter by member ID")
    refill_id: Optional[str] = Field(None, description="Filter by refill ID")
    bundle_id: Optional[str] = Field(None, description="Filter by bundle ID")
    
    # Stage and state filters
    current_stage: Optional[SnapshotStage] = Field(None, description="Filter by current stage")
    pa_state: Optional[PAState] = Field(None, description="Filter by PA state")
    bundle_timing_state: Optional[BundleTimingState] = Field(None, description="Filter by bundle timing")
    
    # Timing filters
    snapshot_timestamp_from: Optional[datetime] = Field(None, description="Snapshot timestamp from")
    snapshot_timestamp_to: Optional[datetime] = Field(None, description="Snapshot timestamp to")
    
    # Pagination
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")
    
    # Sorting
    sort_by: str = Field("snapshot_timestamp", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


class SnapshotList(BaseModel):
    """Response model for snapshot list queries"""
    
    snapshots: List[RefillSnapshot] = Field(..., description="List of snapshots")
    total_count: int = Field(..., description="Total number of snapshots matching query")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")
    has_more: bool = Field(..., description="Whether more results are available")
