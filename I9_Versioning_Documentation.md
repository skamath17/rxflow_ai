# Issue I9: Version Risk and Explainability Logic

## Summary
Implemented an **in-memory version registry** to persist model and explainability versions for audit and traceability. Each risk assessment and explanation is now registered with model metadata, enabling lineage and version tracking without external dependencies.

## Objectives
- Persist **risk model version** and **explainability model version** per artifact.
- Provide a lightweight registry for audit traceability.
- Enable lookups by artifact ID and artifact type.

## Architecture

### Core Components
1. **Versioned Models (`src/models/versioning.py`)**
   - `VersionedArtifactType`: enumerates risk assessment vs. explanation
   - `VersionRecord`: artifact ID + model name/version + metadata + timestamp

2. **Version Registry (`src/utils/version_registry.py`)**
   - In-memory storage of `VersionRecord`
   - Indexes by artifact ID and artifact type
   - API for registration and lookup

3. **Risk & Explainability Integration**
   - Risk scoring engine registers every assessment
   - Explainability engine registers every explanation

## Data Flow
1. Risk scoring produces a risk assessment
2. Version registry registers the assessment with model metadata
3. Explainability generates explanation and registers its version

## Key Design Decisions
- **In-memory registry** (no persistence yet)
- **Minimal metadata schema** to support audit traceability
- **Separation of concerns** between engines and registry

## Implementation Details

### Version Models
- **`VersionRecord`** includes:
  - `artifact_id`, `artifact_type`
  - `model_name`, `model_version`
  - `created_at`, `metadata`, optional `notes`

### Registry Operations
- `register(...)`
- `get(record_id)`
- `list_by_artifact(artifact_id)`
- `list_by_type(artifact_type)`

### Integration Points
- `BundleRiskScoringEngine`
- `BundleRiskExplainabilityEngine`

## Testing
Tests cover:
- Registry insert and lookup
- Risk assessment registration
- Explanation registration

**Tests:**
```
pytest tests/test_versioning
```

## Status
✅ Complete
