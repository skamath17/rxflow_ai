# Issue I17: Generate Synthetic Bundle Scenarios

## Summary
Implemented **synthetic bundle scenarios** to simulate clean bundles, PA‑delayed splits, and OOS‑driven splits. Scenarios emit canonical events to feed downstream pipelines.

## Objectives
- Produce deterministic synthetic event streams
- Cover clean bundles, PA delays, and OOS disruptions
- Provide optional helpers to derive snapshots and metrics

## Architecture

### Core Components
1. **Scenario Models (`src/models/simulation.py`)**
   - `ScenarioType`
   - `SyntheticScenario`

2. **Scenario Generator (`src/simulation/scenario_generator.py`)**
   - Generates canonical events for each scenario type
   - Supports batch generation

3. **Snapshot/Metrics Helper (`src/simulation/snapshot_builder.py`)**
   - `build_snapshot` and `build_metrics` for quick downstream testing

4. **Exports**
   - Models exported in `src/models/__init__.py`
   - Generator exposed via `src/simulation/__init__.py`

## Scenario Types
- **Clean Bundle**: refill lifecycle completes and bundle ships
- **PA‑Delayed Split**: PA delay introduces split risk
- **OOS‑Driven Split**: inventory disruption introduces split risk

## Testing
Tests cover:
- Scenario generation for all types
- Snapshot/metrics helper output

**Tests:**
```
pytest tests/test_simulation
```

## Status
✅ Complete
