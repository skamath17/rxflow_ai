"""
Lineage completeness models for PharmIQ.
"""

from typing import List
from pydantic import BaseModel, Field


class LineageGap(BaseModel):
    """Represents a missing link in the lineage chain."""

    stage: str = Field(..., description="Stage where lineage broke")
    identifier: str = Field(..., description="Identifier missing linkage")
    message: str = Field(..., description="Gap description")


class LineageReport(BaseModel):
    """Summary of lineage completeness check."""

    is_complete: bool
    gaps: List[LineageGap] = Field(default_factory=list)
    total_events: int = 0
    total_snapshots: int = 0
    total_metrics: int = 0
    total_recommendations: int = 0
    total_actions: int = 0
    total_outcomes: int = 0
