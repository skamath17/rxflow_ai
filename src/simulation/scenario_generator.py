"""
Scenario generator for synthetic bundle simulations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from ..models.events import (
    BaseCanonicalEvent,
    EventSource,
    EventType,
    PAStatus,
    RefillStatus,
    create_canonical_event,
)
from ..models.simulation import ScenarioType, SyntheticScenario


class ScenarioGenerator:
    """Generate synthetic bundle scenarios with canonical events."""

    def __init__(self, base_time: datetime | None = None):
        self.base_time = base_time or datetime.now(timezone.utc)

    def generate(self, scenario_type: ScenarioType, bundle_size: int = 2) -> SyntheticScenario:
        if scenario_type == ScenarioType.CLEAN_BUNDLE:
            events = self._generate_clean_bundle(bundle_size)
            description = "Clean bundle ships without disruptions."
        elif scenario_type == ScenarioType.PA_DELAYED_SPLIT:
            events = self._generate_pa_delayed_split(bundle_size)
            description = "PA delay causes bundle split risk."
        elif scenario_type == ScenarioType.OOS_DRIVEN_SPLIT:
            events = self._generate_oos_split(bundle_size)
            description = "Out-of-stock delay causes bundle split risk."
        else:
            raise ValueError(f"Unsupported scenario type: {scenario_type}")

        return SyntheticScenario(
            scenario_id=f"scenario_{uuid.uuid4().hex[:8]}",
            scenario_type=scenario_type,
            description=description,
            events=events,
        )

    def generate_all(self, bundle_size: int = 2) -> List[SyntheticScenario]:
        return [
            self.generate(ScenarioType.CLEAN_BUNDLE, bundle_size=bundle_size),
            self.generate(ScenarioType.PA_DELAYED_SPLIT, bundle_size=bundle_size),
            self.generate(ScenarioType.OOS_DRIVEN_SPLIT, bundle_size=bundle_size),
        ]

    def _generate_clean_bundle(self, bundle_size: int) -> List[BaseCanonicalEvent]:
        events = []
        for idx in range(bundle_size):
            time_offset = timedelta(hours=idx * 2)
            events.extend(self._refill_lifecycle_events(idx, time_offset, status=RefillStatus.SHIPPED))
        events.append(self._bundle_event(EventType.BUNDLE_SHIPPED, bundle_size))
        return events

    def _generate_pa_delayed_split(self, bundle_size: int) -> List[BaseCanonicalEvent]:
        events = []
        for idx in range(bundle_size):
            time_offset = timedelta(hours=idx * 3)
            events.extend(self._refill_lifecycle_events(idx, time_offset, status=RefillStatus.PROCESSING))
        pa_event = create_canonical_event({
            "event_id": self._event_id("pa", 0),
            "member_id": self._member_id(0),
            "refill_id": self._refill_id(0),
            "bundle_id": self._bundle_id(),
            "event_type": EventType.PA_SUBMITTED.value,
            "event_source": EventSource.PA_SYSTEM.value,
            "event_timestamp": (self.base_time + timedelta(hours=6)).isoformat(),
            "received_timestamp": (self.base_time + timedelta(hours=6)).isoformat(),
            "pa_status": PAStatus.SUBMITTED.value,
            "pa_processing_days": 5,
        })
        events.append(pa_event)
        events.append(self._bundle_event(EventType.BUNDLE_SPLIT, bundle_size))
        return events

    def _generate_oos_split(self, bundle_size: int) -> List[BaseCanonicalEvent]:
        events = []
        for idx in range(bundle_size):
            time_offset = timedelta(hours=idx * 3)
            events.extend(self._refill_lifecycle_events(idx, time_offset, status=RefillStatus.BUNDLED))
        oos_event = create_canonical_event({
            "event_id": self._event_id("oos", 0),
            "member_id": self._member_id(0),
            "refill_id": self._refill_id(0),
            "bundle_id": self._bundle_id(),
            "event_type": EventType.OOS_DETECTED.value,
            "event_source": EventSource.INVENTORY_SYSTEM.value,
            "event_timestamp": (self.base_time + timedelta(hours=8)).isoformat(),
            "received_timestamp": (self.base_time + timedelta(hours=8)).isoformat(),
            "oos_status": "detected",
            "oos_reason": "inventory_shortage",
            "oos_duration_days": 4,
        })
        events.append(oos_event)
        events.append(self._bundle_event(EventType.BUNDLE_SPLIT, bundle_size))
        return events

    def _refill_lifecycle_events(
        self,
        idx: int,
        time_offset: timedelta,
        status: RefillStatus,
    ) -> List[BaseCanonicalEvent]:
        base_time = self.base_time + time_offset
        bundle_id = self._bundle_id()
        events = [
            create_canonical_event({
                "event_id": self._event_id("refill_init", idx),
                "member_id": self._member_id(idx),
                "refill_id": self._refill_id(idx),
                "bundle_id": bundle_id,
                "event_type": EventType.REFILL_INITIATED.value,
                "event_source": EventSource.CENTERSYNC.value,
                "event_timestamp": base_time.isoformat(),
                "received_timestamp": base_time.isoformat(),
                "refill_status": RefillStatus.PENDING.value,
            }),
            create_canonical_event({
                "event_id": self._event_id("refill_eligible", idx),
                "member_id": self._member_id(idx),
                "refill_id": self._refill_id(idx),
                "bundle_id": bundle_id,
                "event_type": EventType.REFILL_ELIGIBLE.value,
                "event_source": EventSource.CENTERSYNC.value,
                "event_timestamp": (base_time + timedelta(hours=1)).isoformat(),
                "received_timestamp": (base_time + timedelta(hours=1)).isoformat(),
                "refill_status": RefillStatus.ELIGIBLE.value,
            }),
        ]
        if status in {RefillStatus.BUNDLED, RefillStatus.SHIPPED, RefillStatus.PROCESSING}:
            events.append(
                create_canonical_event({
                    "event_id": self._event_id("refill_bundled", idx),
                    "member_id": self._member_id(idx),
                    "refill_id": self._refill_id(idx),
                    "bundle_id": bundle_id,
                    "event_type": EventType.REFILL_BUNDLED.value,
                    "event_source": EventSource.CENTERSYNC.value,
                    "event_timestamp": (base_time + timedelta(hours=2)).isoformat(),
                    "received_timestamp": (base_time + timedelta(hours=2)).isoformat(),
                    "refill_status": RefillStatus.BUNDLED.value,
                })
            )
        if status == RefillStatus.SHIPPED:
            events.append(
                create_canonical_event({
                    "event_id": self._event_id("refill_shipped", idx),
                    "member_id": self._member_id(idx),
                    "refill_id": self._refill_id(idx),
                    "bundle_id": bundle_id,
                    "event_type": EventType.REFILL_SHIPPED.value,
                    "event_source": EventSource.HPC.value,
                    "event_timestamp": (base_time + timedelta(hours=4)).isoformat(),
                    "received_timestamp": (base_time + timedelta(hours=4)).isoformat(),
                    "refill_status": RefillStatus.SHIPPED.value,
                })
            )
        return events

    def _bundle_event(self, event_type: EventType, bundle_size: int) -> BaseCanonicalEvent:
        return create_canonical_event({
            "event_id": self._event_id("bundle", bundle_size),
            "member_id": self._member_id(0),
            "refill_id": self._refill_id(0),
            "bundle_id": self._bundle_id(),
            "event_type": event_type.value,
            "event_source": EventSource.CENTERSYNC.value,
            "event_timestamp": (self.base_time + timedelta(hours=5)).isoformat(),
            "received_timestamp": (self.base_time + timedelta(hours=5)).isoformat(),
            "total_refills": bundle_size,
            "total_members": bundle_size,
            "member_refills": [
                {"member_id": self._member_id(idx), "refill_id": self._refill_id(idx)}
                for idx in range(bundle_size)
            ],
        })

    def _event_id(self, prefix: str, idx: int) -> str:
        return f"{prefix}_{idx}_{uuid.uuid4().hex[:6]}"

    def _member_id(self, idx: int) -> str:
        return f"member_{idx:02d}_synthetic"

    def _refill_id(self, idx: int) -> str:
        return f"refill_{idx:02d}_synthetic"

    def _bundle_id(self) -> str:
        return "bundle_synthetic"
