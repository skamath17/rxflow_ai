"""Tests for synthetic scenario generator."""

from src.simulation.scenario_generator import ScenarioGenerator
from src.models.simulation import ScenarioType
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
