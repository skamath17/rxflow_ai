"""
In-memory version registry for risk and explainability artifacts.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Iterable

from ..models.versioning import VersionRecord, VersionedArtifactType


class VersionRegistry:
    """Simple in-memory registry for versioned artifacts."""

    def __init__(self):
        self._records: Dict[str, VersionRecord] = {}
        self._artifact_index: Dict[str, List[str]] = {}
        self._type_index: Dict[VersionedArtifactType, List[str]] = {}

    def register(
        self,
        artifact_id: str,
        artifact_type: VersionedArtifactType,
        model_name: str,
        model_version: str,
        metadata: Optional[dict] = None,
        notes: Optional[str] = None,
    ) -> VersionRecord:
        record_id = f"ver_{uuid.uuid4().hex[:10]}"
        record = VersionRecord(
            record_id=record_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            model_name=model_name,
            model_version=model_version,
            metadata=metadata or {},
            notes=notes,
        )
        self._records[record_id] = record
        self._artifact_index.setdefault(artifact_id, []).append(record_id)
        self._type_index.setdefault(artifact_type, []).append(record_id)
        return record

    def get(self, record_id: str) -> Optional[VersionRecord]:
        return self._records.get(record_id)

    def list_by_artifact(self, artifact_id: str) -> List[VersionRecord]:
        return [self._records[rid] for rid in self._artifact_index.get(artifact_id, [])]

    def list_by_type(self, artifact_type: VersionedArtifactType) -> List[VersionRecord]:
        return [self._records[rid] for rid in self._type_index.get(artifact_type, [])]

    def all_records(self) -> Iterable[VersionRecord]:
        return self._records.values()
