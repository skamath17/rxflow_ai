"""
Ops work queue models for bundle risk follow-up.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class QueueItemStatus(str, Enum):
    """Status of a work queue item."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class QueuePriority(str, Enum):
    """Priority levels for ops queue items."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BundleRiskQueueItem(BaseModel):
    """Queue entry representing a bundle risk."""
    queue_id: str
    risk_id: str
    risk_type: str
    risk_severity: str

    bundle_id: Optional[str] = None
    member_id: Optional[str] = None
    refill_id: Optional[str] = None

    title: str
    summary: str
    priority: QueuePriority
    status: QueueItemStatus = QueueItemStatus.OPEN

    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
