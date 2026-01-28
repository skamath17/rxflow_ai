"""
Synthetic scenario models for bundle simulations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List
from pydantic import BaseModel, Field

from .events import BaseCanonicalEvent


class ScenarioType(str, Enum):
    """Types of synthetic bundle scenarios."""
    CLEAN_BUNDLE = "clean_bundle"
    PA_DELAYED_SPLIT = "pa_delayed_split"
    OOS_DRIVEN_SPLIT = "oos_driven_split"


class SyntheticScenario(BaseModel):
    """Synthetic bundle scenario with canonical events."""
    scenario_id: str
    scenario_type: ScenarioType
    description: str
    events: List[BaseCanonicalEvent]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UniformRange(BaseModel):
    """Uniform range used for simulation sampling."""
    minimum: float
    maximum: float


class SimulationConfig(BaseModel):
    """Configurable distributions for synthetic scenarios."""
    pa_processing_days: UniformRange = Field(default_factory=lambda: UniformRange(minimum=2, maximum=7))
    oos_duration_days: UniformRange = Field(default_factory=lambda: UniformRange(minimum=1, maximum=5))
    refill_gap_days: UniformRange = Field(default_factory=lambda: UniformRange(minimum=20, maximum=35))
