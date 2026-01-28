"""
Pytest configuration and fixtures for PharmIQ tests.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any
from src.models.events import (
    EventType,
    EventSource,
    RefillStatus,
    PAStatus,
    RefillEvent,
    PAEvent,
    OSEvent,
    BundleEvent
)


@pytest.fixture
def sample_utc_datetime():
    """Sample UTC datetime for testing"""
    return datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def base_event_data(sample_utc_datetime):
    """Base event data for testing"""
    return {
        "event_id": "evt_1234567890abcdef",
        "member_id": "mem_1234567890abcdef",
        "refill_id": "ref_1234567890abcdef",
        "bundle_id": "bun_1234567890abcdef",
        "event_type": "refill_initiated",
        "event_source": "centersync",
        "event_timestamp": sample_utc_datetime.isoformat(),
        "received_timestamp": sample_utc_datetime.isoformat(),
        "source_event_id": "src_evt_123",
        "source_system": "centersync_v2",
        "source_timestamp": sample_utc_datetime.isoformat(),
        "bundle_member_count": 3,
        "bundle_refill_count": 5,
        "bundle_sequence": 2,
        "correlation_id": "corr_1234567890",
        "causation_id": "caus_1234567890",
        "version": "1.0"
    }


@pytest.fixture
def sample_refill_event_data(base_event_data, sample_utc_datetime):
    """Sample refill event data"""
    return {
        **base_event_data,
        "event_id": "evt_refill_1234567890abcdef",
        "member_id": "mem_refill_1234567890abcdef", 
        "refill_id": "ref_refill_1234567890abcdef",
        "event_type": "refill_eligible",
        "drug_ndc": "123456789012",
        "drug_name": "Lisinopril",
        "days_supply": 30,
        "quantity": 10.0,
        "refill_due_date": sample_utc_datetime.isoformat(),
        "ship_by_date": sample_utc_datetime.isoformat(),
        "last_fill_date": sample_utc_datetime.isoformat(),
        "refill_status": "eligible",
        "source_status": "ELIGIBLE_FOR_BUNDLING",
        "days_until_due": 5,
        "days_since_last_fill": 25,
        "bundle_alignment_score": 0.85
    }


@pytest.fixture
def sample_pa_event_data(base_event_data, sample_utc_datetime):
    """Sample PA event data"""
    return {
        **base_event_data,
        "event_id": "evt_pa_1234567890abcdef",
        "member_id": "mem_pa_1234567890abcdef",
        "refill_id": "ref_pa_1234567890abcdef",
        "event_type": "pa_approved",
        "pa_status": "approved",
        "pa_type": "renewal",
        "pa_submitted_date": sample_utc_datetime.isoformat(),
        "pa_response_date": sample_utc_datetime.isoformat(),
        "pa_expiry_date": sample_utc_datetime.isoformat(),
        "pa_processing_days": 2,
        "pa_validity_days": 365,
        "pa_reason_code": "J45.909",
        "pa_outcome": "Approved with quantity limit",
        "source_pa_id": "pa_123456789"
    }


@pytest.fixture
def sample_oos_event_data(base_event_data, sample_utc_datetime):
    """Sample OOS event data"""
    return {
        **base_event_data,
        "event_id": "evt_oos_1234567890abcdef",
        "member_id": "mem_oos_1234567890abcdef",
        "refill_id": "ref_oos_1234567890abcdef",
        "event_type": "oos_detected",
        "oos_status": "detected",
        "oos_reason": "manufacturer_shortage",
        "oos_detected_date": sample_utc_datetime.isoformat(),
        "oos_resolved_date": None,
        "oos_duration_days": None,
        "estimated_resupply_date": sample_utc_datetime.isoformat(),
        "affected_quantity": 100.0,
        "alternative_available": False,
        "source_oos_id": "oos_123456789"
    }


@pytest.fixture
def sample_bundle_event_data(base_event_data, sample_utc_datetime):
    """Sample bundle event data"""
    return {
        **base_event_data,
        "event_id": "evt_bundle_1234567890abcdef",
        "member_id": "mem_bundle_1234567890abcdef",
        "refill_id": "ref_bundle_1234567890abcdef",
        "event_type": "bundle_formed",
        "bundle_type": "standard",
        "bundle_strategy": "timing_optimized",
        "bundle_formed_date": sample_utc_datetime.isoformat(),
        "bundle_ship_date": sample_utc_datetime.isoformat(),
        "member_refills": [
            {"member_id": "mem_12345678abcd", "refill_id": "ref_4567890abcd"},
            {"member_id": "mem_7890abcd1234", "refill_id": "ref_01234567abcd"}
        ],
        "total_refills": 5,
        "total_members": 3,
        "bundle_efficiency_score": 0.92,
        "bundle_complexity_score": 0.35,
        "split_risk_score": 0.15
    }
