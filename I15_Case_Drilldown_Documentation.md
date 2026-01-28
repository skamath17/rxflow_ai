# Issue I15: Build Bundle Risk Case Drill-Down

## Summary
Implemented a **case drill‑down layer** that assembles timeline, drivers, bundle context, and recommended actions for investigating bundle risk cases.

## Objectives
- Provide a structured case view for bundle risk investigations
- Surface timeline events, drivers, and recommendations
- Link actions and outcomes for audit-ready drill‑down

## Architecture

### Core Components
1. **Case Models (`src/models/case_drilldown.py`)**
   - `BundleRiskCase`
   - `DrilldownTimelineEvent`
   - `CaseStatus`

2. **Case Drill-Down Engine (`src/case_drilldown/case_drilldown_engine.py`)**
   - Builds `BundleRiskCase` from risk, snapshots, recommendations, actions, outcomes
   - Constructs timeline and summary

3. **Exports**
   - Models exported in `src/models/__init__.py`
   - Engine exposed via `src/case_drilldown/__init__.py`

## Data Flow
1. Risk engine emits risk assessment
2. Case drill‑down engine assembles timeline, drivers, recommendations
3. Actions/outcomes augment the case view

## Timeline Events
- Risk assessment recorded
- Snapshot captures (stage, PA state, bundle timing)

## Testing
Tests cover:
- Case creation with timeline and summary

**Tests:**
```
pytest tests/test_case_drilldown
```

## Status
✅ Complete
