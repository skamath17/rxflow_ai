"""
Executive savings dashboard models.
"""

from datetime import datetime, timezone
from typing import Dict
from pydantic import BaseModel, Field


class ExecutiveSavingsSnapshot(BaseModel):
    """Summary metrics for executive savings visibility."""
    total_shipments_reduced: int
    total_outreach_suppressed: int
    total_cost_savings: float
    outcomes_tracked: int
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, float] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
