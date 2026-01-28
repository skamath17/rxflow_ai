"""
Deterministic replay for synthetic bundle scenarios.
"""

from __future__ import annotations

from typing import Dict

from ..models.simulation import ReplayConfig, SyntheticScenario
from .scenario_generator import ScenarioGenerator


class ScenarioReplayEngine:
    """Replay synthetic scenarios deterministically using stored seeds."""

    def __init__(self):
        self._replay_configs: Dict[str, ReplayConfig] = {}

    def register(self, replay_id: str, config: ReplayConfig) -> None:
        self._replay_configs[replay_id] = config

    def replay(self, replay_id: str) -> SyntheticScenario:
        config = self._replay_configs[replay_id]
        generator = ScenarioGenerator(
            config=config.simulation_config,
            seed=config.seed,
            base_time=config.base_time,
        )
        return generator.generate(config.scenario_type, bundle_size=config.bundle_size)

    def get_config(self, replay_id: str) -> ReplayConfig | None:
        return self._replay_configs.get(replay_id)
