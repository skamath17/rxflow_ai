# Issue I19: Replay Bundle Risk Simulations

## Summary
Implemented **deterministic replay** of synthetic scenarios using stored seeds and configurations so that the same scenario can be regenerated identically.

## Objectives
- Provide seed-based deterministic replay
- Persist replay configuration for regeneration
- Ensure consistent timestamps and event IDs across replays

## Architecture

### Core Components
1. **Replay Config (`src/models/simulation.py`)**
   - `ReplayConfig` captures scenario type, bundle size, seed, base time, and simulation config

2. **Seeded Scenario Generator (`src/simulation/scenario_generator.py`)**
   - Uses a local RNG seeded per replay
   - Deterministic event IDs and timing

3. **Replay Engine (`src/simulation/replay_engine.py`)**
   - Stores replay configs and regenerates scenarios on demand

4. **Exports**
   - `ReplayConfig` exported in `src/models/__init__.py`
   - `ScenarioReplayEngine` exported in `src/simulation/__init__.py`

## Replay Flow
1. Register a `ReplayConfig` with seed and config
2. Replay engine regenerates events using the same seed + base time
3. Results are identical across replays

## Testing
Tests cover:
- Deterministic replay of the same scenario config

**Tests:**
```
pytest tests/test_simulation
```

## Status
✅ Complete
