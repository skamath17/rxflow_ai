"""
Action tracking models for bundle-preserving interventions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ActionStatus(str, Enum):
    """Lifecycle status for tracked actions."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionOutcome(str, Enum):
    """Outcome status for completed actions."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNKNOWN = "unknown"


class TrackedAction(BaseModel):
    """Tracked action tied to a recommendation and approval decision."""
    action_id: str
    recommendation_id: str
    action_type: str
    status: ActionStatus = ActionStatus.PROPOSED
    outcome: ActionOutcome = ActionOutcome.UNKNOWN

    bundle_id: Optional[str] = None
    member_id: Optional[str] = None
    refill_id: Optional[str] = None

    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
