"""
Versioning models for risk and explainability artifacts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class VersionedArtifactType(str, Enum):
    """Types of versioned artifacts."""
    RISK_ASSESSMENT = "risk_assessment"
    EXPLANATION = "explanation"


class VersionRecord(BaseModel):
    """Record of a versioned artifact for audit traceability."""
    record_id: str
    artifact_id: str
    artifact_type: VersionedArtifactType
    model_name: str
    model_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
