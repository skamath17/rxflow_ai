"""
Case drill-down models for bundle risk investigations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    """Status for a drill-down case."""
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


class DrilldownTimelineEvent(BaseModel):
    """Timeline event for a case drill-down."""
    timestamp: datetime
    label: str
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BundleRiskCase(BaseModel):
    """Detailed case view for a bundle risk."""
    case_id: str
    risk_id: str
    risk_type: str
    severity: str

    bundle_id: Optional[str] = None
    member_id: Optional[str] = None
    refill_id: Optional[str] = None

    status: CaseStatus = CaseStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    timeline: List[DrilldownTimelineEvent] = Field(default_factory=list)
    drivers: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    outcomes: List[Dict[str, Any]] = Field(default_factory=list)

    summary: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
