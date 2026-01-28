"""
Outcome tracking models for bundle and outreach results.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class OutcomeType(str, Enum):
    """Types of measurable outcomes."""
    SHIPMENT_REDUCTION = "shipment_reduction"
    OUTREACH_SUPPRESSION = "outreach_suppression"


class OutcomeStatus(str, Enum):
    """Lifecycle status for an outcome measurement."""
    PENDING = "pending"
    MEASURED = "measured"
    CONFIRMED = "confirmed"


class BundleOutcome(BaseModel):
    """Outcome measurement linked to tracked actions."""
    outcome_id: str
    action_id: str
    recommendation_id: str
    outcome_type: OutcomeType
    status: OutcomeStatus = OutcomeStatus.PENDING

    bundle_id: Optional[str] = None
    member_id: Optional[str] = None
    refill_id: Optional[str] = None

    baseline_shipments: Optional[int] = None
    actual_shipments: Optional[int] = None
    shipments_reduced: Optional[int] = None

    baseline_outreach: Optional[int] = None
    actual_outreach: Optional[int] = None
    outreach_suppressed: Optional[int] = None

    cost_savings_estimate: Optional[float] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class OutcomeSummary(BaseModel):
    """Aggregated outcome results."""
    total_outcomes: int
    shipment_reduction_total: int
    outreach_suppression_total: int
    total_cost_savings: float
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
