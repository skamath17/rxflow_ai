"""Tests for deterministic scenario replay."""

from datetime import datetime, timezone

from src.simulation.replay_engine import ScenarioReplayEngine
from src.models.simulation import ReplayConfig, ScenarioType, SimulationConfig, UniformRange


def test_replay_deterministic():
    config = ReplayConfig(
        scenario_type=ScenarioType.PA_DELAYED_SPLIT,
        bundle_size=2,
        seed=42,
        base_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        simulation_config=SimulationConfig(
            pa_processing_days=UniformRange(minimum=3, maximum=6),
            oos_duration_days=UniformRange(minimum=2, maximum=4),
            refill_gap_days=UniformRange(minimum=20, maximum=25),
        ),
    )

    engine = ScenarioReplayEngine()
    engine.register("replay_1", config)
    first = engine.replay("replay_1")
    second = engine.replay("replay_1")

    assert [event.model_dump() for event in first.events] == [event.model_dump() for event in second.events]
