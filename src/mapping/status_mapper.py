"""
Status to Bundle-Event Mapping for PharmIQ

Deterministic mapping from source system statuses to bundle-aware canonical events.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re

from src.models.events import (
    EventType, EventSource, RefillStatus, PAStatus, BaseCanonicalEvent,
    RefillEvent, PAEvent, OSEvent, BundleEvent
)


class MappingConfidence(str, Enum):
    """Confidence levels for status mapping"""
    HIGH = "high"        # Direct 1:1 mapping
    MEDIUM = "medium"    # Context-dependent mapping
    LOW = "low"          # Ambiguous mapping requiring review


@dataclass
class MappingResult:
    """Result of status mapping operation"""
    success: bool
    canonical_event_type: EventType
    canonical_status: Optional[str]
    confidence: MappingConfidence
    bundle_context: Optional[Dict[str, Any]] = None
    mapping_rules_applied: List[str] = None
    warnings: List[str] = None
    requires_manual_review: bool = False
    
    def __post_init__(self):
        if self.mapping_rules_applied is None:
            self.mapping_rules_applied = []
        if self.warnings is None:
            self.warnings = []


class StatusMappingRule:
    """Individual status mapping rule"""
    
    def __init__(self, 
                 source_system: str,
                 source_status: str,
                 canonical_event_type: EventType,
                 canonical_status: Optional[str],
                 confidence: MappingConfidence,
                 description: str,
                 conditions: Optional[Dict[str, Any]] = None,
                 bundle_context: Optional[Dict[str, Any]] = None):
        self.source_system = source_system
        self.source_status = source_status
        self.canonical_event_type = canonical_event_type
        self.canonical_status = canonical_status
        self.confidence = confidence
        self.description = description
        self.conditions = conditions or {}
        self.bundle_context = bundle_context or {}
    
    def matches(self, source_system: str, source_status: str, context: Dict[str, Any]) -> bool:
        """Check if this rule matches the given context"""
        if source_system != self.source_system:
            return False
        
        # Exact match or regex pattern
        if isinstance(self.source_status, str):
            if self.source_status.startswith("regex:"):
                pattern = self.source_status[6:]  # Remove "regex:" prefix
                return bool(re.match(pattern, source_status, re.IGNORECASE))
            else:
                return source_status.upper() == self.source_status.upper()
        
        return False
    
    def evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate conditional mapping rules"""
        if not self.conditions:
            return True
        
        for field, expected_value in self.conditions.items():
            actual_value = context.get(field)
            if actual_value is None:
                return False
            
            # Handle different condition types
            if isinstance(expected_value, dict):
                # Complex condition with operator
                operator = expected_value.get("operator", "equals")
                value = expected_value.get("value")
                
                if operator == "equals":
                    if actual_value != value:
                        return False
                elif operator == "contains":
                    if value not in str(actual_value):
                        return False
                elif operator == "greater_than":
                    if not (isinstance(actual_value, (int, float)) and actual_value > value):
                        return False
                elif operator == "less_than":
                    if not (isinstance(actual_value, (int, float)) and actual_value < value):
                        return False
                elif operator == "in":
                    if actual_value not in value:
                        return False
            else:
                # Simple equality check
                if actual_value != expected_value:
                    return False
        
        return True


class StatusMapper:
    """Deterministic status to bundle-event mapping"""
    
    def __init__(self):
        self.rules: List[StatusMappingRule] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default status mapping rules"""
        
        # CenterSync Refill Status Mappings
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="ELIGIBLE_FOR_BUNDLING",
            canonical_event_type=EventType.REFILL_ELIGIBLE,
            canonical_status=RefillStatus.ELIGIBLE,
            confidence=MappingConfidence.HIGH,
            description="Refill eligible for bundling"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="BUNDLED",
            canonical_event_type=EventType.REFILL_BUNDLED,
            canonical_status=RefillStatus.BUNDLED,
            confidence=MappingConfidence.HIGH,
            description="Refill successfully bundled"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="SHIPPED",
            canonical_event_type=EventType.REFILL_SHIPPED,
            canonical_status=RefillStatus.SHIPPED,
            confidence=MappingConfidence.HIGH,
            description="Refill shipped"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="COMPLETED",
            canonical_event_type=EventType.REFILL_COMPLETED,
            canonical_status=RefillStatus.COMPLETED,
            confidence=MappingConfidence.HIGH,
            description="Refill completed"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="CANCELLED",
            canonical_event_type=EventType.REFILL_CANCELLED,
            canonical_status=RefillStatus.CANCELLED,
            confidence=MappingConfidence.HIGH,
            description="Refill cancelled"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="ON_HOLD",
            canonical_event_type=EventType.REFILL_INITIATED,
            canonical_status=RefillStatus.ON_HOLD,
            confidence=MappingConfidence.MEDIUM,
            description="Refill on hold (treated as initiated with special status)"
        ))
        
        # CenterSync PA Status Mappings
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="PA_REQUIRED",
            canonical_event_type=EventType.PA_SUBMITTED,
            canonical_status=PAStatus.SUBMITTED,
            confidence=MappingConfidence.HIGH,
            description="Prior authorization required and submitted"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="PA_APPROVED",
            canonical_event_type=EventType.PA_APPROVED,
            canonical_status=PAStatus.APPROVED,
            confidence=MappingConfidence.HIGH,
            description="Prior authorization approved"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="PA_DENIED",
            canonical_event_type=EventType.PA_DENIED,
            canonical_status=PAStatus.DENIED,
            confidence=MappingConfidence.HIGH,
            description="Prior authorization denied"
        ))
        
        # HPIE/HPC Status Mappings
        self.add_rule(StatusMappingRule(
            source_system="hpie",
            source_status="ORDER_CREATED",
            canonical_event_type=EventType.REFILL_INITIATED,
            canonical_status=RefillStatus.PENDING,
            confidence=MappingConfidence.HIGH,
            description="Order created in HPIE"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="hpie",
            source_status="ORDER_SHIPPED",
            canonical_event_type=EventType.REFILL_SHIPPED,
            canonical_status=RefillStatus.SHIPPED,
            confidence=MappingConfidence.HIGH,
            description="Order shipped from HPIE"
        ))
        
        # PA System Status Mappings
        self.add_rule(StatusMappingRule(
            source_system="pa_system",
            source_status="SUBMITTED",
            canonical_event_type=EventType.PA_SUBMITTED,
            canonical_status=PAStatus.SUBMITTED,
            confidence=MappingConfidence.HIGH,
            description="PA submitted to external system"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="pa_system",
            source_status="IN_REVIEW",
            canonical_event_type=EventType.PA_SUBMITTED,
            canonical_status=PAStatus.IN_REVIEW,
            confidence=MappingConfidence.MEDIUM,
            description="PA under review"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="pa_system",
            source_status="APPROVED",
            canonical_event_type=EventType.PA_APPROVED,
            canonical_status=PAStatus.APPROVED,
            confidence=MappingConfidence.HIGH,
            description="PA approved by external system"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="pa_system",
            source_status="DENIED",
            canonical_event_type=EventType.PA_DENIED,
            canonical_status=PAStatus.DENIED,
            confidence=MappingConfidence.HIGH,
            description="PA denied by external system"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="pa_system",
            source_status="EXPIRED",
            canonical_event_type=EventType.PA_EXPIRED,
            canonical_status=PAStatus.EXPIRED,
            confidence=MappingConfidence.HIGH,
            description="PA approval expired"
        ))
        
        # Inventory System Status Mappings
        self.add_rule(StatusMappingRule(
            source_system="inventory_system",
            source_status="OUT_OF_STOCK",
            canonical_event_type=EventType.OOS_DETECTED,
            canonical_status="detected",
            confidence=MappingConfidence.HIGH,
            description="Out of stock detected"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="inventory_system",
            source_status="IN_STOCK",
            canonical_event_type=EventType.OOS_RESOLVED,
            canonical_status="resolved",
            confidence=MappingConfidence.HIGH,
            description="Out of stock resolved"
        ))
        
        # Bundle-Specific Mappings with Context
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="BUNDLE_FORMED",
            canonical_event_type=EventType.BUNDLE_FORMED,
            canonical_status=None,
            confidence=MappingConfidence.HIGH,
            description="Bundle formed",
            bundle_context={"bundle_type": "standard"}
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="BUNDLE_SPLIT",
            canonical_event_type=EventType.BUNDLE_SPLIT,
            canonical_status=None,
            confidence=MappingConfidence.HIGH,
            description="Bundle split",
            bundle_context={"split_reason": "timing_mismatch"}
        ))
        
        # Conditional Mappings
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="PENDING",
            canonical_event_type=EventType.REFILL_INITIATED,
            canonical_status=RefillStatus.PENDING,
            confidence=MappingConfidence.MEDIUM,
            description="Pending status (context-dependent)",
            conditions={
                "days_supply": {"operator": "greater_than", "value": 0},
                "quantity": {"operator": "greater_than", "value": 0}
            }
        ))
        
        # Regex-based Mappings for Status Variations
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="regex:.*PA.*REQUIRED.*",
            canonical_event_type=EventType.PA_SUBMITTED,
            canonical_status=PAStatus.SUBMITTED,
            confidence=MappingConfidence.MEDIUM,
            description="PA required (regex pattern)"
        ))
        
        self.add_rule(StatusMappingRule(
            source_system="centersync",
            source_status="regex:.*SHIPPED.*",
            canonical_event_type=EventType.REFILL_SHIPPED,
            canonical_status=RefillStatus.SHIPPED,
            confidence=MappingConfidence.MEDIUM,
            description="Shipped status (regex pattern)"
        ))
    
    def add_rule(self, rule: StatusMappingRule):
        """Add a new mapping rule"""
        self.rules.append(rule)
    
    def map_status(self, 
                   source_system: str,
                   source_status: str,
                   context: Dict[str, Any] = None) -> MappingResult:
        """Map source system status to canonical event"""
        context = context or {}
        
        # Find matching rules
        matching_rules = []
        for rule in self.rules:
            if rule.matches(source_system, source_status, context):
                if rule.evaluate_conditions(context):
                    matching_rules.append(rule)
        
        if not matching_rules:
            return MappingResult(
                success=False,
                canonical_event_type=EventType.REFILL_INITIATED,  # Default
                canonical_status=RefillStatus.PENDING,
                confidence=MappingConfidence.LOW,
                warnings=[f"No mapping rule found for {source_system}:{source_status}"],
                requires_manual_review=True
            )
        
        # Select best rule (highest confidence)
        best_rule = max(matching_rules, key=lambda r: (
            0 if r.confidence == MappingConfidence.HIGH else
            1 if r.confidence == MappingConfidence.MEDIUM else 2
        ))
        
        # Check for multiple high-confidence matches (ambiguity)
        high_confidence_matches = [r for r in matching_rules if r.confidence == MappingConfidence.HIGH]
        warnings = []
        requires_review = False
        
        if len(high_confidence_matches) > 1:
            warnings.append(f"Multiple high-confidence matches found for {source_system}:{source_status}")
            requires_review = True
        
        # Build bundle context
        bundle_context = best_rule.bundle_context.copy() if best_rule.bundle_context else {}
        
        # Add context-based bundle information
        if context.get("bundle_id"):
            bundle_context["has_bundle_id"] = True
        if context.get("bundle_member_count", 0) > 1:
            bundle_context["is_multi_member"] = True
        
        return MappingResult(
            success=True,
            canonical_event_type=best_rule.canonical_event_type,
            canonical_status=best_rule.canonical_status,
            confidence=best_rule.confidence,
            bundle_context=bundle_context if bundle_context else None,
            mapping_rules_applied=[best_rule.description],
            warnings=warnings,
            requires_manual_review=requires_review
        )
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get mapping rule statistics"""
        stats = {
            "total_rules": len(self.rules),
            "rules_by_source": {},
            "rules_by_confidence": {
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "rules_by_event_type": {}
        }
        
        for rule in self.rules:
            # Count by source system
            source = rule.source_system
            stats["rules_by_source"][source] = stats["rules_by_source"].get(source, 0) + 1
            
            # Count by confidence
            stats["rules_by_confidence"][rule.confidence.value] += 1
            
            # Count by event type
            event_type = rule.canonical_event_type.value
            stats["rules_by_event_type"][event_type] = stats["rules_by_event_type"].get(event_type, 0) + 1
        
        return stats
    
    def validate_mapping_consistency(self) -> List[str]:
        """Validate mapping rule consistency"""
        issues = []
        
        # Check for duplicate exact matches
        exact_matches = {}
        for rule in self.rules:
            if not rule.source_status.startswith("regex:"):
                key = f"{rule.source_system}:{rule.source_status}"
                if key in exact_matches:
                    issues.append(f"Duplicate exact match: {key}")
                else:
                    exact_matches[key] = rule
        
        # Check for rules without descriptions
        for i, rule in enumerate(self.rules):
            if not rule.description or not rule.description.strip():
                issues.append(f"Rule {i} missing description: {rule.source_system}:{rule.source_status}")
        
        # Check for low confidence rules without conditions
        for i, rule in enumerate(self.rules):
            if rule.confidence == MappingConfidence.LOW and not rule.conditions:
                issues.append(f"Low confidence rule {i} without conditions: {rule.source_system}:{rule.source_status}")
        
        return issues
    
    def export_mapping_rules(self) -> List[Dict[str, Any]]:
        """Export mapping rules for documentation"""
        exported = []
        
        for rule in self.rules:
            exported.append({
                "source_system": rule.source_system,
                "source_status": rule.source_status,
                "canonical_event_type": rule.canonical_event_type.value,
                "canonical_status": rule.canonical_status.value if hasattr(rule.canonical_status, 'value') else rule.canonical_status,
                "confidence": rule.confidence.value,
                "description": rule.description,
                "conditions": rule.conditions,
                "bundle_context": rule.bundle_context
            })
        
        return exported
