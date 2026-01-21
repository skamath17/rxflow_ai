"""
Guardrail models for human approval of recommendations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Approval lifecycle states."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class ApprovalDecision(BaseModel):
    """Human approval decision for a recommendation."""
    recommendation_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: Optional[str] = None
    decision_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
