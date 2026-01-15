"""
Tests for status to bundle-event mapping.
"""

import pytest
from datetime import datetime, timezone

from src.mapping.status_mapper import StatusMapper, StatusMappingRule, MappingConfidence, MappingResult
from src.models.events import EventType, RefillStatus, PAStatus


class TestStatusMappingRule:
    """Test StatusMappingRule functionality"""
    
    def test_exact_match_rule(self):
        """Test exact status matching"""
        rule = StatusMappingRule(
            source_system="centersync",
            source_status="ELIGIBLE_FOR_BUNDLING",
            canonical_event_type=EventType.REFILL_ELIGIBLE,
            canonical_status=RefillStatus.ELIGIBLE,
            confidence=MappingConfidence.HIGH,
            description="Test rule"
        )
        
        assert rule.matches("centersync", "ELIGIBLE_FOR_BUNDLING", {})
        assert rule.matches("centersync", "eligible_for_bundling", {})  # Case insensitive
        assert not rule.matches("hpie", "ELIGIBLE_FOR_BUNDLING", {})
        assert not rule.matches("centersync", "SHIPPED", {})
    
    def test_regex_match_rule(self):
        """Test regex pattern matching"""
        rule = StatusMappingRule(
            source_system="centersync",
            source_status="regex:.*SHIPPED.*",
            canonical_event_type=EventType.REFILL_SHIPPED,
            canonical_status=RefillStatus.SHIPPED,
            confidence=MappingConfidence.MEDIUM,
            description="Regex rule"
        )
        
        assert rule.matches("centersync", "SHIPPED", {})
        assert rule.matches("centersync", "PARTIALLY_SHIPPED", {})
        assert rule.matches("centersync", "shipped_today", {})
        assert not rule.matches("centersync", "PENDING", {})
        assert not rule.matches("hpie", "SHIPPED", {})
    
    def test_conditional_rule_evaluation(self):
        """Test conditional rule evaluation"""
        rule = StatusMappingRule(
            source_system="centersync",
            source_status="PENDING",
            canonical_event_type=EventType.REFILL_INITIATED,
            canonical_status=RefillStatus.PENDING,
            confidence=MappingConfidence.MEDIUM,
            description="Conditional rule",
            conditions={
                "days_supply": {"operator": "greater_than", "value": 0},
                "quantity": {"operator": "greater_than", "value": 0}
            }
        )
        
        # Matching context
        matching_context = {
            "days_supply": 30,
            "quantity": 10
        }
        assert rule.evaluate_conditions(matching_context)
        
        # Non-matching context
        non_matching_context = {
            "days_supply": 0,
            "quantity": 10
        }
        assert not rule.evaluate_conditions(non_matching_context)
        
        # Missing field
        missing_context = {
            "days_supply": 30
        }
        assert not rule.evaluate_conditions(missing_context)
    
    def test_contains_operator_condition(self):
        """Test 'contains' operator in conditions"""
        rule = StatusMappingRule(
            source_system="centersync",
            source_status="SPECIAL",
            canonical_event_type=EventType.REFILL_INITIATED,
            canonical_status=RefillStatus.PENDING,
            confidence=MappingConfidence.MEDIUM,
            description="Contains rule",
            conditions={
                "drug_name": {"operator": "contains", "value": "Lisinopril"}
            }
        )
        
        assert rule.evaluate_conditions({"drug_name": "Lisinopril 10mg"})
        assert rule.evaluate_conditions({"drug_name": "Generic Lisinopril"})
        assert not rule.evaluate_conditions({"drug_name": "Metformin"})
    
    def test_in_operator_condition(self):
        """Test 'in' operator in conditions"""
        rule = StatusMappingRule(
            source_system="centersync",
            source_status="CHECKED",
            canonical_event_type=EventType.REFILL_ELIGIBLE,
            canonical_status=RefillStatus.ELIGIBLE,
            confidence=MappingConfidence.HIGH,
            description="In operator rule",
            conditions={
                "source_status": {"operator": "in", "value": ["ELIGIBLE", "APPROVED", "CHECKED"]}
            }
        )
        
        assert rule.evaluate_conditions({"source_status": "ELIGIBLE"})
        assert rule.evaluate_conditions({"source_status": "CHECKED"})
        assert not rule.evaluate_conditions({"source_status": "DENIED"})


class TestStatusMapper:
    """Test StatusMapper functionality"""
    
    @pytest.fixture
    def mapper(self):
        """Create status mapper with default rules"""
        return StatusMapper()
    
    def test_high_confidence_mapping(self, mapper):
        """Test high confidence status mapping"""
        result = mapper.map_status("centersync", "ELIGIBLE_FOR_BUNDLING")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.REFILL_ELIGIBLE
        assert result.canonical_status == RefillStatus.ELIGIBLE
        assert result.confidence == MappingConfidence.HIGH
        assert len(result.warnings) == 0
        assert result.requires_manual_review is False
    
    def test_medium_confidence_mapping(self, mapper):
        """Test medium confidence status mapping"""
        result = mapper.map_status("centersync", "ON_HOLD")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.REFILL_INITIATED
        assert result.canonical_status == RefillStatus.ON_HOLD
        assert result.confidence == MappingConfidence.MEDIUM
    
    def test_regex_mapping(self, mapper):
        """Test regex-based status mapping"""
        result = mapper.map_status("centersync", "PARTIALLY_SHIPPED")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.REFILL_SHIPPED
        assert result.canonical_status == RefillStatus.SHIPPED
        assert result.confidence == MappingConfidence.MEDIUM
    
    def test_no_mapping_found(self, mapper):
        """Test behavior when no mapping rule is found"""
        result = mapper.map_status("unknown_system", "UNKNOWN_STATUS")
        
        assert result.success is False
        assert result.canonical_event_type == EventType.REFILL_INITIATED  # Default
        assert result.canonical_status == RefillStatus.PENDING
        assert result.confidence == MappingConfidence.LOW
        assert len(result.warnings) > 0
        assert result.requires_manual_review is True
        assert "No mapping rule found" in result.warnings[0]
    
    def test_conditional_mapping_success(self, mapper):
        """Test conditional mapping with matching context"""
        context = {
            "days_supply": 30,
            "quantity": 10
        }
        result = mapper.map_status("centersync", "PENDING", context)
        
        assert result.success is True
        assert result.canonical_event_type == EventType.REFILL_INITIATED
        assert result.canonical_status == RefillStatus.PENDING
        assert result.confidence == MappingConfidence.MEDIUM
    
    def test_conditional_mapping_failure(self, mapper):
        """Test conditional mapping with non-matching context"""
        context = {
            "days_supply": 0,  # Fails condition
            "quantity": 10
        }
        result = mapper.map_status("centersync", "PENDING", context)
        
        # Should fall back to default behavior
        assert result.success is False
        assert result.confidence == MappingConfidence.LOW
    
    def test_bundle_context_mapping(self, mapper):
        """Test bundle context in mapping results"""
        result = mapper.map_status("centersync", "BUNDLE_FORMED")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.BUNDLE_FORMED
        assert result.bundle_context is not None
        assert result.bundle_context.get("bundle_type") == "standard"
    
    def test_context_based_bundle_context(self, mapper):
        """Test bundle context derived from event context"""
        context = {
            "bundle_id": "bundle_123",
            "bundle_member_count": 3
        }
        result = mapper.map_status("centersync", "ELIGIBLE_FOR_BUNDLING", context)
        
        assert result.bundle_context is not None
        assert result.bundle_context.get("has_bundle_id") is True
        assert result.bundle_context.get("is_multi_member") is True
    
    def test_multiple_high_confidence_matches(self, mapper):
        """Test handling of multiple high-confidence matches"""
        # Add a duplicate rule for testing
        duplicate_rule = StatusMappingRule(
            source_system="centersync",
            source_status="ELIGIBLE_FOR_BUNDLING",
            canonical_event_type=EventType.REFILL_ELIGIBLE,
            canonical_status=RefillStatus.ELIGIBLE,
            confidence=MappingConfidence.HIGH,
            description="Duplicate rule"
        )
        mapper.add_rule(duplicate_rule)
        
        result = mapper.map_status("centersync", "ELIGIBLE_FOR_BUNDLING")
        
        assert result.success is True
        assert len(result.warnings) > 0
        assert "Multiple high-confidence matches" in result.warnings[0]
        assert result.requires_manual_review is True
    
    def test_pa_status_mapping(self, mapper):
        """Test PA status mappings"""
        result = mapper.map_status("pa_system", "APPROVED")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.PA_APPROVED
        assert result.canonical_status == PAStatus.APPROVED
        assert result.confidence == MappingConfidence.HIGH
    
    def test_oos_status_mapping(self, mapper):
        """Test OOS status mappings"""
        result = mapper.map_status("inventory_system", "OUT_OF_STOCK")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.OOS_DETECTED
        assert result.canonical_status == "detected"
        assert result.confidence == MappingConfidence.HIGH
    
    def test_mapping_statistics(self, mapper):
        """Test mapping statistics generation"""
        stats = mapper.get_mapping_statistics()
        
        assert "total_rules" in stats
        assert "rules_by_source" in stats
        assert "rules_by_confidence" in stats
        assert "rules_by_event_type" in stats
        
        assert stats["total_rules"] > 0
        assert "centersync" in stats["rules_by_source"]
        assert stats["rules_by_confidence"]["high"] > 0
        assert stats["rules_by_confidence"]["medium"] > 0
    
    def test_mapping_consistency_validation(self, mapper):
        """Test mapping rule consistency validation"""
        # Add a rule without description for testing
        bad_rule = StatusMappingRule(
            source_system="test",
            source_status="TEST",
            canonical_event_type=EventType.REFILL_INITIATED,
            canonical_status=RefillStatus.PENDING,
            confidence=MappingConfidence.HIGH,
            description=""  # Empty description
        )
        mapper.add_rule(bad_rule)
        
        issues = mapper.validate_mapping_consistency()
        
        assert len(issues) > 0
        assert any("missing description" in issue for issue in issues)
    
    def test_export_mapping_rules(self, mapper):
        """Test mapping rules export"""
        exported = mapper.export_mapping_rules()
        
        assert isinstance(exported, list)
        assert len(exported) > 0
        
        # Check structure of exported rule
        rule = exported[0]
        assert "source_system" in rule
        assert "source_status" in rule
        assert "canonical_event_type" in rule
        assert "canonical_status" in rule
        assert "confidence" in rule
        assert "description" in rule
    
    def test_add_custom_rule(self, mapper):
        """Test adding custom mapping rule"""
        custom_rule = StatusMappingRule(
            source_system="custom_system",
            source_status="CUSTOM_STATUS",
            canonical_event_type=EventType.REFILL_ELIGIBLE,
            canonical_status=RefillStatus.ELIGIBLE,
            confidence=MappingConfidence.HIGH,
            description="Custom test rule"
        )
        
        initial_count = len(mapper.rules)
        mapper.add_rule(custom_rule)
        
        assert len(mapper.rules) == initial_count + 1
        
        # Test the new rule works
        result = mapper.map_status("custom_system", "CUSTOM_STATUS")
        assert result.success is True
        assert result.canonical_event_type == EventType.REFILL_ELIGIBLE
    
    def test_case_insensitive_matching(self, mapper):
        """Test case insensitive status matching"""
        result_lower = mapper.map_status("centersync", "eligible_for_bundling")
        result_upper = mapper.map_status("centersync", "ELIGIBLE_FOR_BUNDLING")
        result_mixed = mapper.map_status("centersync", "Eligible_For_Bundling")
        
        # All should return the same result
        assert result_lower.success == result_upper.success == result_mixed.success
        assert result_lower.canonical_event_type == result_upper.canonical_event_type == result_mixed.canonical_event_type
    
    def test_hpie_status_mapping(self, mapper):
        """Test HPIE system status mapping"""
        result = mapper.map_status("hpie", "ORDER_CREATED")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.REFILL_INITIATED
        assert result.canonical_status == RefillStatus.PENDING
        assert result.confidence == MappingConfidence.HIGH
    
    def test_bundle_split_mapping(self, mapper):
        """Test bundle split status mapping"""
        result = mapper.map_status("centersync", "BUNDLE_SPLIT")
        
        assert result.success is True
        assert result.canonical_event_type == EventType.BUNDLE_SPLIT
        assert result.bundle_context is not None
        assert result.bundle_context.get("split_reason") == "timing_mismatch"


class TestMappingIntegration:
    """Integration tests for status mapping"""
    
    def test_end_to_end_mapping_workflow(self):
        """Test complete mapping workflow"""
        mapper = StatusMapper()
        
        # Test various source systems and statuses
        test_cases = [
            ("centersync", "ELIGIBLE_FOR_BUNDLING", EventType.REFILL_ELIGIBLE),
            ("centersync", "SHIPPED", EventType.REFILL_SHIPPED),
            ("pa_system", "APPROVED", EventType.PA_APPROVED),
            ("inventory_system", "OUT_OF_STOCK", EventType.OOS_DETECTED),
            ("hpie", "ORDER_CREATED", EventType.REFILL_INITIATED)
        ]
        
        for source_system, source_status, expected_event_type in test_cases:
            result = mapper.map_status(source_system, source_status)
            
            assert result.success is True
            assert result.canonical_event_type == expected_event_type
            assert result.confidence in [MappingConfidence.HIGH, MappingConfidence.MEDIUM]
    
    def test_mapping_with_rich_context(self):
        """Test mapping with rich event context"""
        mapper = StatusMapper()
        
        context = {
            "bundle_id": "bundle_123",
            "bundle_member_count": 3,
            "days_supply": 30,
            "quantity": 10,
            "drug_name": "Lisinopril"
        }
        
        result = mapper.map_status("centersync", "ELIGIBLE_FOR_BUNDLING", context)
        
        assert result.success is True
        assert result.bundle_context is not None
        assert result.bundle_context.get("has_bundle_id") is True
        assert result.bundle_context.get("is_multi_member") is True
