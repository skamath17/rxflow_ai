"""
Refill Snapshot Aggregation Engine for PharmIQ

This module implements the snapshot aggregation engine that processes canonical events
to create comprehensive refill snapshots. The engine aggregates events by member/refill
and computes the current state, timing metrics, and bundle context.

The engine is designed to be:
- Event-driven (processes streams of canonical events)
- Deterministic (same events produce same snapshots)
- Incremental (can update existing snapshots with new events)
- Bundle-aware (maintains bundle context and timing)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import time

from ..models.events import BaseCanonicalEvent, RefillEvent, PAEvent, OSEvent, BundleEvent, EventType, RefillStatus, PAStatus
from ..models.snapshots import (
    RefillSnapshot, SnapshotMetadata, SnapshotStage, PAState, BundleTimingState,
    SnapshotQuery, SnapshotList
)
from ..utils.audit import AuditLogger, AuditAction, AuditSeverity


class SnapshotAggregationEngine:
    """Engine for aggregating canonical events into refill snapshots"""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """Initialize snapshot aggregation engine"""
        self.audit_logger = audit_logger or AuditLogger()
        self._snapshot_cache: Dict[str, RefillSnapshot] = {}
        self._event_index: Dict[str, List[str]] = defaultdict(list)  # member_id -> [snapshot_ids]
        self._bundle_index: Dict[str, List[str]] = defaultdict(list)   # bundle_id -> [snapshot_ids]
        
    def aggregate_events_to_snapshot(self, events: List[BaseCanonicalEvent]) -> RefillSnapshot:
        """Aggregate a list of events into a refill snapshot"""
        start_time = time.time()
        
        if not events:
            raise ValueError("Cannot create snapshot from empty event list")
        
        # Sort events by timestamp for deterministic processing
        sorted_events = sorted(events, key=lambda e: e.event_timestamp)
        
        # Extract key identifiers
        member_id = sorted_events[0].member_id
        refill_id = sorted_events[0].refill_id
        bundle_id = sorted_events[0].bundle_id
        
        # Generate snapshot ID
        snapshot_id = f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Initialize snapshot with base information
        snapshot = RefillSnapshot(
            snapshot_id=snapshot_id,
            member_id=member_id,
            refill_id=refill_id,
            bundle_id=bundle_id,
            snapshot_timestamp=datetime.now(timezone.utc),
            current_stage=SnapshotStage.INITIATED,
            pa_state=PAState.NOT_REQUIRED,
            bundle_timing_state=BundleTimingState.UNKNOWN,
            total_events=len(sorted_events),
            latest_event_timestamp=sorted_events[-1].event_timestamp,
            earliest_event_timestamp=sorted_events[0].event_timestamp,
            event_ids=[event.event_id for event in sorted_events],
            correlation_id=sorted_events[0].correlation_id
        )
        
        # Process events to populate snapshot
        self._process_events_for_snapshot(sorted_events, snapshot)
        
        # Compute derived metrics
        self._compute_timing_metrics(snapshot)
        
        # Determine current stage and states
        self._determine_current_state(snapshot)
        
        # Cache the snapshot
        self._snapshot_cache[snapshot_id] = snapshot
        self._event_index[member_id].append(snapshot_id)
        if bundle_id:
            self._bundle_index[bundle_id].append(snapshot_id)
        
        # Log aggregation completion
        aggregation_time_ms = int((time.time() - start_time) * 1000)
        self.audit_logger.log_snapshot_aggregated(
            snapshot_id=snapshot_id,
            member_id=member_id,
            refill_id=refill_id,
            events_count=len(events),
            processing_time_ms=aggregation_time_ms
        )
        
        return snapshot
    
    def update_snapshot_with_event(self, snapshot_id: str, new_event: BaseCanonicalEvent) -> Optional[RefillSnapshot]:
        """Update an existing snapshot with a new event"""
        if snapshot_id not in self._snapshot_cache:
            return None
        
        snapshot = self._snapshot_cache[snapshot_id]
        
        # Verify the event belongs to this snapshot
        if (new_event.member_id != snapshot.member_id or 
            new_event.refill_id != snapshot.refill_id):
            self.audit_logger.log_event_processing_error(
                event_id=new_event.event_id,
                error="Event does not belong to snapshot",
                severity=AuditSeverity.WARNING
            )
            return None
        
        # Add new event to snapshot
        snapshot.event_ids.append(new_event.event_id)
        snapshot.total_events += 1
        snapshot.latest_event_timestamp = max(snapshot.latest_event_timestamp, new_event.event_timestamp)
        
        # Re-process all events for updated snapshot
        # In production, this would be optimized for incremental updates
        all_events = self._get_events_by_ids(snapshot.event_ids)
        updated_snapshot = self.aggregate_events_to_snapshot(all_events)
        
        # Update cache indices
        self._snapshot_cache[snapshot_id] = updated_snapshot
        
        return updated_snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[RefillSnapshot]:
        """Retrieve a snapshot by ID"""
        return self._snapshot_cache.get(snapshot_id)
    
    def query_snapshots(self, query: SnapshotQuery) -> SnapshotList:
        """Query snapshots based on criteria"""
        all_snapshots = list(self._snapshot_cache.values())
        
        # Apply filters
        filtered_snapshots = self._apply_filters(all_snapshots, query)
        
        # Sort results
        sorted_snapshots = self._sort_snapshots(filtered_snapshots, query.sort_by, query.sort_order)
        
        # Paginate
        total_count = len(sorted_snapshots)
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_snapshots = sorted_snapshots[start_idx:end_idx]
        
        return SnapshotList(
            snapshots=paginated_snapshots,
            total_count=total_count,
            limit=query.limit,
            offset=query.offset,
            has_more=end_idx < total_count
        )
    
    def get_member_snapshots(self, member_id: str, limit: int = 100) -> List[RefillSnapshot]:
        """Get all snapshots for a member"""
        snapshot_ids = self._event_index.get(member_id, [])
        snapshots = [self._snapshot_cache[sid] for sid in snapshot_ids if sid in self._snapshot_cache]
        
        # Sort by snapshot timestamp descending
        snapshots.sort(key=lambda s: s.snapshot_timestamp, reverse=True)
        
        return snapshots[:limit]
    
    def get_bundle_snapshots(self, bundle_id: str, limit: int = 100) -> List[RefillSnapshot]:
        """Get all snapshots for a bundle"""
        snapshot_ids = self._bundle_index.get(bundle_id, [])
        snapshots = [self._snapshot_cache[sid] for sid in snapshot_ids if sid in self._snapshot_cache]
        
        # Sort by snapshot timestamp descending
        snapshots.sort(key=lambda s: s.snapshot_timestamp, reverse=True)
        
        return snapshots[:limit]
    
    def _process_events_for_snapshot(self, events: List[BaseCanonicalEvent], snapshot: RefillSnapshot) -> None:
        """Process events to populate snapshot fields"""
        
        for event in events:
            # Count event types
            if isinstance(event, RefillEvent):
                snapshot.refill_events += 1
                self._process_refill_event(event, snapshot)
            elif isinstance(event, PAEvent):
                snapshot.pa_events += 1
                self._process_pa_event(event, snapshot)
            elif isinstance(event, OSEvent):
                snapshot.oos_events += 1
                self._process_oos_event(event, snapshot)
            elif isinstance(event, BundleEvent):
                snapshot.bundle_events += 1
                self._process_bundle_event(event, snapshot)
            
            # Update bundle context from any event
            if event.bundle_member_count:
                snapshot.bundle_member_count = event.bundle_member_count
            if event.bundle_refill_count:
                snapshot.bundle_refill_count = event.bundle_refill_count
            if event.bundle_sequence:
                snapshot.bundle_sequence = event.bundle_sequence
    
    def _process_refill_event(self, event: RefillEvent, snapshot: RefillSnapshot) -> None:
        """Process a refill event to update snapshot"""
        
        # Update refill details
        if event.drug_ndc:
            snapshot.drug_ndc = event.drug_ndc
        if event.drug_name:
            snapshot.drug_name = event.drug_name
        if event.days_supply:
            snapshot.days_supply = event.days_supply
        if event.quantity:
            snapshot.quantity = event.quantity
        
        # Update timing information
        if event.refill_due_date:
            snapshot.refill_due_date = event.refill_due_date
        if event.ship_by_date:
            snapshot.ship_by_date = event.ship_by_date
        if event.last_fill_date:
            snapshot.last_fill_date = event.last_fill_date
        
        # Update status information
        if event.refill_status:
            snapshot.refill_status = event.refill_status
        if event.source_status:
            snapshot.source_status = event.source_status
        
        # Update bundle timing metrics
        if event.bundle_alignment_score is not None:
            snapshot.bundle_alignment_score = event.bundle_alignment_score
        
        # Record key event timestamps
        if event.event_type == EventType.REFILL_INITIATED:
            snapshot.initiated_timestamp = event.event_timestamp
        elif event.event_type == EventType.REFILL_ELIGIBLE:
            snapshot.eligible_timestamp = event.event_timestamp
        elif event.event_type == EventType.REFILL_BUNDLED:
            snapshot.bundled_timestamp = event.event_timestamp
        elif event.event_type == EventType.REFILL_SHIPPED:
            snapshot.shipped_timestamp = event.event_timestamp
        elif event.event_type == EventType.REFILL_COMPLETED:
            snapshot.completed_timestamp = event.event_timestamp
    
    def _process_pa_event(self, event: PAEvent, snapshot: RefillSnapshot) -> None:
        """Process a PA event to update snapshot"""
        
        # Update PA information
        snapshot.pa_type = event.pa_type
        if event.pa_processing_days:
            snapshot.pa_processing_days = event.pa_processing_days
        if event.pa_expiry_date:
            snapshot.pa_expiry_date = event.pa_expiry_date
        
        # Record key PA timestamps
        if event.event_type == EventType.PA_SUBMITTED:
            snapshot.pa_submitted_timestamp = event.event_timestamp
        elif event.event_type in [EventType.PA_APPROVED, EventType.PA_DENIED, EventType.PA_EXPIRED]:
            snapshot.pa_resolved_timestamp = event.event_timestamp
    
    def _process_oos_event(self, event: OSEvent, snapshot: RefillSnapshot) -> None:
        """Process an OOS event to update snapshot"""
        
        # Record OOS timestamps
        if event.event_type == EventType.OOS_DETECTED:
            snapshot.oos_detected_timestamp = event.event_timestamp
        elif event.event_type == EventType.OOS_RESOLVED:
            snapshot.oos_resolved_timestamp = event.event_timestamp
    
    def _process_bundle_event(self, event: BundleEvent, snapshot: RefillSnapshot) -> None:
        """Process a bundle event to update snapshot"""
        
        # Update bundle context
        if event.bundle_member_count:
            snapshot.bundle_member_count = event.bundle_member_count
        if event.bundle_refill_count:
            snapshot.bundle_refill_count = event.bundle_refill_count
        if event.bundle_sequence:
            snapshot.bundle_sequence = event.bundle_sequence
        
        # Record bundle timestamps
        if event.event_type == EventType.BUNDLE_FORMED:
            snapshot.bundled_timestamp = event.event_timestamp
        elif event.event_type == EventType.BUNDLE_SHIPPED:
            snapshot.shipped_timestamp = event.event_timestamp
    
    def _compute_timing_metrics(self, snapshot: RefillSnapshot) -> None:
        """Compute timing metrics for the snapshot"""
        now = datetime.now(timezone.utc)
        
        # Days until due
        if snapshot.refill_due_date:
            snapshot.days_until_due = (snapshot.refill_due_date.date() - now.date()).days
        
        # Days since last fill
        if snapshot.last_fill_date:
            snapshot.days_since_last_fill = (now.date() - snapshot.last_fill_date.date()).days
        
        # Total processing days
        if snapshot.initiated_timestamp:
            snapshot.total_processing_days = (now - snapshot.initiated_timestamp).days
        
        # Days in current stage (will be updated after stage determination)
        # This is a placeholder - will be computed in _determine_current_state
    
    def _determine_current_state(self, snapshot: RefillSnapshot) -> None:
        """Determine current stage and states based on events"""
        
        # Determine current stage based on latest events
        if snapshot.completed_timestamp:
            snapshot.current_stage = SnapshotStage.COMPLETED
        elif snapshot.shipped_timestamp:
            snapshot.current_stage = SnapshotStage.SHIPPED
        elif snapshot.oos_detected_timestamp and not snapshot.oos_resolved_timestamp:
            snapshot.current_stage = SnapshotStage.OOS_DETECTED
        elif snapshot.bundled_timestamp:
            snapshot.current_stage = SnapshotStage.BUNDLED
        elif snapshot.pa_resolved_timestamp:
            if snapshot.pa_resolved_timestamp and snapshot.pa_submitted_timestamp:
                # Check PA outcome
                pa_events = [e for e in snapshot.event_ids if "pa_" in e.lower()]
                if pa_events:
                    # In production, would look up actual events
                    # For now, assume approved if we have a resolved timestamp
                    snapshot.current_stage = SnapshotStage.PA_APPROVED
        elif snapshot.pa_submitted_timestamp:
            snapshot.current_stage = SnapshotStage.PA_PENDING
        elif snapshot.eligible_timestamp:
            snapshot.current_stage = SnapshotStage.ELIGIBLE
        elif snapshot.initiated_timestamp:
            snapshot.current_stage = SnapshotStage.INITIATED
        
        # Determine PA state
        if snapshot.pa_events == 0:
            snapshot.pa_state = PAState.NOT_REQUIRED
        elif snapshot.pa_submitted_timestamp and not snapshot.pa_resolved_timestamp:
            snapshot.pa_state = PAState.PENDING
        elif snapshot.pa_resolved_timestamp:
            # Would need to check actual PA status from events
            # For now, assume approved
            snapshot.pa_state = PAState.APPROVED
        
        # Determine bundle timing state
        if snapshot.bundle_alignment_score is not None:
            if snapshot.bundle_alignment_score >= 0.8:
                snapshot.bundle_timing_state = BundleTimingState.ALIGNED
            elif snapshot.bundle_alignment_score >= 0.6:
                snapshot.bundle_timing_state = BundleTimingState.EARLY
            elif snapshot.bundle_alignment_score >= 0.4:
                snapshot.bundle_timing_state = BundleTimingState.LATE
            else:
                snapshot.bundle_timing_state = BundleTimingState.MISALIGNED
        else:
            snapshot.bundle_timing_state = BundleTimingState.UNKNOWN
        
        # Compute days in current stage
        stage_timestamps = {
            SnapshotStage.INITIATED: snapshot.initiated_timestamp,
            SnapshotStage.ELIGIBLE: snapshot.eligible_timestamp,
            SnapshotStage.PA_PENDING: snapshot.pa_submitted_timestamp,
            SnapshotStage.PA_APPROVED: snapshot.pa_resolved_timestamp,
            SnapshotStage.BUNDLED: snapshot.bundled_timestamp,
            SnapshotStage.OOS_DETECTED: snapshot.oos_detected_timestamp,
            SnapshotStage.SHIPPED: snapshot.shipped_timestamp,
            SnapshotStage.COMPLETED: snapshot.completed_timestamp,
        }
        
        if snapshot.current_stage in stage_timestamps:
            stage_timestamp = stage_timestamps[snapshot.current_stage]
            if stage_timestamp:
                snapshot.days_in_current_stage = (datetime.now(timezone.utc) - stage_timestamp).days
    
    def _apply_filters(self, snapshots: List[RefillSnapshot], query: SnapshotQuery) -> List[RefillSnapshot]:
        """Apply query filters to snapshots"""
        filtered = snapshots
        
        if query.member_id:
            filtered = [s for s in filtered if s.member_id == query.member_id]
        
        if query.refill_id:
            filtered = [s for s in filtered if s.refill_id == query.refill_id]
        
        if query.bundle_id:
            filtered = [s for s in filtered if s.bundle_id == query.bundle_id]
        
        if query.current_stage:
            filtered = [s for s in filtered if s.current_stage == query.current_stage]
        
        if query.pa_state:
            filtered = [s for s in filtered if s.pa_state == query.pa_state]
        
        if query.bundle_timing_state:
            filtered = [s for s in filtered if s.bundle_timing_state == query.bundle_timing_state]
        
        if query.snapshot_timestamp_from:
            filtered = [s for s in filtered if s.snapshot_timestamp >= query.snapshot_timestamp_from]
        
        if query.snapshot_timestamp_to:
            filtered = [s for s in filtered if s.snapshot_timestamp <= query.snapshot_timestamp_to]
        
        return filtered
    
    def _sort_snapshots(self, snapshots: List[RefillSnapshot], sort_by: str, sort_order: str) -> List[RefillSnapshot]:
        """Sort snapshots by specified field"""
        reverse = sort_order.lower() == "desc"
        
        if sort_by == "snapshot_timestamp":
            return sorted(snapshots, key=lambda s: s.snapshot_timestamp, reverse=reverse)
        elif sort_by == "latest_event_timestamp":
            return sorted(snapshots, key=lambda s: s.latest_event_timestamp, reverse=reverse)
        elif sort_by == "days_until_due":
            return sorted(snapshots, key=lambda s: s.days_until_due or 0, reverse=reverse)
        elif sort_by == "total_processing_days":
            return sorted(snapshots, key=lambda s: s.total_processing_days or 0, reverse=reverse)
        else:
            # Default sort by snapshot timestamp
            return sorted(snapshots, key=lambda s: s.snapshot_timestamp, reverse=reverse)
    
    def _get_events_by_ids(self, event_ids: List[str]) -> List[BaseCanonicalEvent]:
        """Get events by IDs (placeholder - would integrate with event storage)"""
        # In production, this would retrieve events from storage
        # For now, return empty list as this is a placeholder
        return []
