# Issue I18: Parameterize Timing & Inventory Distributions

## Summary
Implemented **configurable uniform-range distributions** for synthetic scenario timing and inventory parameters, enabling controlled simulation of PA delays, OOS durations, and refill gap timing.

## Objectives
- Provide configurable distributions for PA processing days
- Provide configurable distributions for OOS duration days
- Provide configurable distributions for refill timing gaps
- Allow scenario generator to sample from these ranges

## Architecture

### Core Components
1. **Simulation Config Models (`src/models/simulation.py`)**
   - `UniformRange`
   - `SimulationConfig`

2. **Scenario Generator Updates (`src/simulation/scenario_generator.py`)**
   - Samples uniform ranges for PA processing days, OOS duration days, refill gap days

3. **Testing Updates**
   - Added tests for custom range configuration

## Configuration Example
```
SimulationConfig(
    pa_processing_days=UniformRange(minimum=3, maximum=7),
    oos_duration_days=UniformRange(minimum=1, maximum=4),
    refill_gap_days=UniformRange(minimum=20, maximum=35),
)
```

## Testing
Tests cover:
- Scenario generation with default ranges
- Scenario generation with custom fixed ranges

**Tests:**
```
pytest tests/test_simulation
```

## Status
✅ Complete
