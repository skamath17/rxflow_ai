"""
Bundle Detection for PharmIQ

Detects bundle context and relationships between events.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from src.models.events import BaseCanonicalEvent, EventType


@dataclass
class BundleContext:
    """Bundle context information"""
    bundle_id: Optional[str] = None
    member_count: int = 0
    refill_count: int = 0
    formation_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    member_ids: Set[str] = field(default_factory=set)
    refill_ids: Set[str] = field(default_factory=set)
    bundle_type: str = "unknown"
    bundle_status: str = "forming"
    risk_factors: List[str] = field(default_factory=list)
    
    def add_event(self, event: BaseCanonicalEvent):
        """Add event to bundle context"""
        self.refill_ids.add(event.refill_id)
        self.member_ids.add(event.member_id)
        self.last_activity = event.event_timestamp
        
        # Update counts
        self.member_count = len(self.member_ids)
        self.refill_count = len(self.refill_ids)
        
        # Update bundle type based on events (only for BundleEvent)
        if hasattr(event, 'bundle_type') and event.bundle_type:
            self.bundle_type = event.bundle_type
    
    def is_complete(self) -> bool:
        """Check if bundle is complete"""
        return self.bundle_status == "completed"
    
    def age_in_hours(self) -> float:
        """Get bundle age in hours"""
        if not self.formation_time:
            return 0.0
        return (datetime.now(timezone.utc) - self.formation_time).total_seconds() / 3600


class BundleDetector:
    """Detects and tracks bundle context"""
    
    def __init__(self):
        self.active_bundles: Dict[str, BundleContext] = {}
        self.completed_bundles: Dict[str, BundleContext] = {}
        self.bundle_relationships: Dict[str, List[str]] = defaultdict(list)  # member_id -> bundle_ids
    
    def detect_bundle_context(self, event: BaseCanonicalEvent) -> BundleContext:
        """Detect bundle context for an event"""
        
        # If event has explicit bundle_id, use existing or create new
        if event.bundle_id:
            bundle_context = self._get_or_create_bundle(event.bundle_id)
            bundle_context.add_event(event)
            return bundle_context
        
        # Try to infer bundle context from timing and relationships
        inferred_context = self._infer_bundle_context(event)
        if inferred_context:
            return inferred_context
        
        # Create individual bundle context
        return self._create_individual_bundle(event)
    
    def _get_or_create_bundle(self, bundle_id: str) -> BundleContext:
        """Get existing bundle or create new one"""
        if bundle_id in self.active_bundles:
            return self.active_bundles[bundle_id]
        
        if bundle_id in self.completed_bundles:
            return self.completed_bundles[bundle_id]
        
        # Create new bundle
        bundle_context = BundleContext(bundle_id=bundle_id)
        self.active_bundles[bundle_id] = bundle_context
        return bundle_context
    
    def _infer_bundle_context(self, event: BaseCanonicalEvent) -> Optional[BundleContext]:
        """Infer bundle context from event relationships"""
        
        # Look for recent events from same member
        recent_bundles = self._find_recent_member_bundles(event.member_id, event.event_timestamp)
        
        if recent_bundles:
            # Use most recent bundle
            bundle_id = recent_bundles[0]
            bundle_context = self.active_bundles.get(bundle_id)
            if bundle_context:
                bundle_context.add_event(event)
                return bundle_context
        
        # Look for timing-based bundle formation
        timing_bundle = self._detect_timing_based_bundle(event)
        if timing_bundle:
            return timing_bundle
        
        return None
    
    def _find_recent_member_bundles(self, member_id: str, timestamp: datetime, 
                                   hours_window: int = 24) -> List[str]:
        """Find recent bundles for a member"""
        recent_bundles = []
        
        for bundle_id, bundle_context in self.active_bundles.items():
            if (member_id in bundle_context.member_ids and 
                bundle_context.last_activity and
                abs((timestamp - bundle_context.last_activity).total_seconds()) < hours_window * 3600):
                recent_bundles.append(bundle_id)
        
        # Sort by last activity (most recent first)
        recent_bundles.sort(key=lambda bid: self.active_bundles[bid].last_activity or datetime.min, reverse=True)
        return recent_bundles
    
    def _detect_timing_based_bundle(self, event: BaseCanonicalEvent) -> Optional[BundleContext]:
        """Detect bundle based on timing patterns"""
        
        # Look for events with similar timing (within 2 hours)
        timing_window = timedelta(hours=2)
        candidate_events = []
        
        for bundle_id, bundle_context in self.active_bundles.items():
            if (bundle_context.last_activity and
                abs((event.event_timestamp - bundle_context.last_activity)) <= timing_window):
                candidate_events.append((bundle_id, bundle_context))
        
        if candidate_events:
            # Select bundle with most similar timing
            best_bundle = min(candidate_events, 
                            key=lambda x: abs((event.event_timestamp - x[1].last_activity)))
            bundle_context = best_bundle[1]
            bundle_context.add_event(event)
            return bundle_context
        
        return None
    
    def _create_individual_bundle(self, event: BaseCanonicalEvent) -> BundleContext:
        """Create individual bundle context"""
        bundle_id = f"individual_{event.member_id}_{event.event_timestamp.strftime('%Y%m%d%H%M%S')}"
        bundle_context = BundleContext(
            bundle_id=bundle_id,
            bundle_type="individual",
            bundle_status="active"
        )
        bundle_context.add_event(event)
        self.active_bundles[bundle_id] = bundle_context
        
        # Track member relationship
        self.bundle_relationships[event.member_id].append(bundle_id)
        
        return bundle_context
    
    def complete_bundle(self, bundle_id: str, completion_reason: str = "shipped") -> BundleContext:
        """Mark bundle as completed"""
        if bundle_id in self.active_bundles:
            bundle_context = self.active_bundles.pop(bundle_id)
            bundle_context.bundle_status = completion_reason
            self.completed_bundles[bundle_id] = bundle_context
            return bundle_context
        
        return None
    
    def analyze_bundle_risks(self, bundle_id: str) -> List[str]:
        """Analyze risk factors for a bundle"""
        bundle_context = self.active_bundles.get(bundle_id) or self.completed_bundles.get(bundle_id)
        
        if not bundle_context:
            return []
        
        risk_factors = []
        
        # Age-based risks
        age_hours = bundle_context.age_in_hours()
        if age_hours > 48:
            risk_factors.append("bundle_age_over_48h")
        elif age_hours > 24:
            risk_factors.append("bundle_age_over_24h")
        
        # Size-based risks
        if bundle_context.member_count > 5:
            risk_factors.append("large_bundle_over_5_members")
        elif bundle_context.refill_count > 10:
            risk_factors.append("large_bundle_over_10_refills")
        
        # Inactivity risks
        if bundle_context.last_activity:
            inactive_hours = (datetime.now(timezone.utc) - bundle_context.last_activity).total_seconds() / 3600
            if inactive_hours > 12:
                risk_factors.append("bundle_inactive_over_12h")
        
        # Type-specific risks
        if bundle_context.bundle_type == "complex":
            risk_factors.append("complex_bundle_type")
        
        bundle_context.risk_factors = risk_factors
        return risk_factors
    
    def get_bundle_statistics(self) -> Dict[str, Any]:
        """Get bundle detection statistics"""
        stats = {
            "active_bundles": len(self.active_bundles),
            "completed_bundles": len(self.completed_bundles),
            "total_members": len(self.bundle_relationships),
            "average_bundle_size": 0,
            "bundle_types": defaultdict(int),
            "risk_distribution": defaultdict(int)
        }
        
        # Calculate average bundle size
        all_bundles = list(self.active_bundles.values()) + list(self.completed_bundles.values())
        if all_bundles:
            stats["average_bundle_size"] = sum(b.refill_count for b in all_bundles) / len(all_bundles)
        
        # Count bundle types
        for bundle in all_bundles:
            stats["bundle_types"][bundle.bundle_type] += 1
        
        # Count risk factors
        for bundle in all_bundles:
            for risk in bundle.risk_factors:
                stats["risk_distribution"][risk] += 1
        
        return dict(stats)
    
    def find_related_events(self, event: BaseCanonicalEvent, max_events: int = 10) -> List[BaseCanonicalEvent]:
        """Find events related to the given event"""
        related_events = []
        
        # Events from same bundle
        if event.bundle_id:
            bundle_context = self.active_bundles.get(event.bundle_id) or self.completed_bundles.get(event.bundle_id)
            if bundle_context:
                # This would need access to actual event store
                # For now, return empty list
                pass
        
        # Events from same member in similar timeframe
        member_bundles = self.bundle_relationships.get(event.member_id, [])
        for bundle_id in member_bundles:
            bundle_context = self.active_bundles.get(bundle_id) or self.completed_bundles.get(bundle_id)
            if bundle_context:
                # Would fetch actual events here
                pass
        
        return related_events[:max_events]
    
    def cleanup_old_bundles(self, max_age_hours: int = 168) -> int:  # 1 week
        """Clean up old completed bundles"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        old_bundles = []
        
        for bundle_id, bundle_context in list(self.completed_bundles.items()):
            if (bundle_context.last_activity and 
                bundle_context.last_activity < cutoff_time):
                old_bundles.append(bundle_id)
        
        for bundle_id in old_bundles:
            del self.completed_bundles[bundle_id]
        
        return len(old_bundles)
    
    def export_bundle_contexts(self) -> Dict[str, Any]:
        """Export bundle contexts for analysis"""
        export_data = {
            "active_bundles": {},
            "completed_bundles": {},
            "member_relationships": dict(self.bundle_relationships)
        }
        
        for bundle_id, bundle_context in self.active_bundles.items():
            export_data["active_bundles"][bundle_id] = {
                "member_count": bundle_context.member_count,
                "refill_count": bundle_context.refill_count,
                "bundle_type": bundle_context.bundle_type,
                "bundle_status": bundle_context.bundle_status,
                "formation_time": bundle_context.formation_time.isoformat() if bundle_context.formation_time else None,
                "last_activity": bundle_context.last_activity.isoformat() if bundle_context.last_activity else None,
                "member_ids": list(bundle_context.member_ids),
                "refill_ids": list(bundle_context.refill_ids),
                "risk_factors": bundle_context.risk_factors
            }
        
        for bundle_id, bundle_context in self.completed_bundles.items():
            export_data["completed_bundles"][bundle_id] = {
                "member_count": bundle_context.member_count,
                "refill_count": bundle_context.refill_count,
                "bundle_type": bundle_context.bundle_type,
                "bundle_status": bundle_context.bundle_status,
                "formation_time": bundle_context.formation_time.isoformat() if bundle_context.formation_time else None,
                "last_activity": bundle_context.last_activity.isoformat() if bundle_context.last_activity else None,
                "member_ids": list(bundle_context.member_ids),
                "refill_ids": list(bundle_context.refill_ids),
                "risk_factors": bundle_context.risk_factors
            }
        
        return export_data
