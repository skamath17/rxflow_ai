"""
Recommendation models for bundle-aware actions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class RecommendationActionType(str, Enum):
    """Action types for bundle-aware recommendations."""
    DELAY = "delay"
    ADVANCE = "advance"
    SUPPRESS = "suppress"
    OUTREACH = "outreach"
    MONITOR = "monitor"


class RecommendationPriority(str, Enum):
    """Priority levels for recommendations."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationContext(BaseModel):
    """Context attached to recommendation decisions."""
    bundle_id: Optional[str] = None
    member_id: Optional[str] = None
    refill_id: Optional[str] = None
    risk_type: Optional[str] = None
    risk_severity: Optional[str] = None
    metrics_snapshot_id: Optional[str] = None
    notes: Dict[str, Any] = Field(default_factory=dict)


class BundleRecommendation(BaseModel):
    """Recommendation output for bundle-aware actions."""
    recommendation_id: str
    action_type: RecommendationActionType
    priority: RecommendationPriority
    title: str
    description: str
    action_steps: List[str] = Field(default_factory=list)
    expected_impact: str
    confidence_score: float = Field(ge=0, le=1)
    time_to_implement: str
    rationale: List[str] = Field(default_factory=list)
    context: RecommendationContext
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
