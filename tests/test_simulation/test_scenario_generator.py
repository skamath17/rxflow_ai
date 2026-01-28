"""Tests for synthetic scenario generator."""

from src.simulation.scenario_generator import ScenarioGenerator
from src.models.simulation import ScenarioType, SimulationConfig, UniformRange
from src.simulation.snapshot_builder import build_snapshot_and_metrics


def test_generate_clean_bundle():
    generator = ScenarioGenerator()
    scenario = generator.generate(ScenarioType.CLEAN_BUNDLE, bundle_size=2)
    assert scenario.events
    assert scenario.scenario_type == ScenarioType.CLEAN_BUNDLE

    snapshot, metrics = build_snapshot_and_metrics(scenario.events)
    assert snapshot.bundle_timing_state.value in {"aligned", "misaligned"}
    assert metrics.bundle_alignment.bundle_alignment_score is not None


def test_generate_pa_split():
    generator = ScenarioGenerator()
    scenario = generator.generate(ScenarioType.PA_DELAYED_SPLIT, bundle_size=2)
    assert scenario.events
    assert scenario.scenario_type == ScenarioType.PA_DELAYED_SPLIT


def test_generate_oos_split():
    generator = ScenarioGenerator()
    scenario = generator.generate(ScenarioType.OOS_DRIVEN_SPLIT, bundle_size=2)
    assert scenario.events
    assert scenario.scenario_type == ScenarioType.OOS_DRIVEN_SPLIT


def test_generate_with_custom_ranges():
    config = SimulationConfig(
        pa_processing_days=UniformRange(minimum=3, maximum=3),
        oos_duration_days=UniformRange(minimum=2, maximum=2),
        refill_gap_days=UniformRange(minimum=25, maximum=25),
    )
    generator = ScenarioGenerator(config=config)
    scenario = generator.generate(ScenarioType.PA_DELAYED_SPLIT, bundle_size=1)
    pa_events = [event for event in scenario.events if getattr(event, "pa_processing_days", None) is not None]
    assert pa_events
    assert pa_events[0].pa_processing_days == 3
