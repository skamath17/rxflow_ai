"""
Executive savings dashboard engine.
"""

from __future__ import annotations

from typing import List

from ..models.executive_dashboard import ExecutiveSavingsSnapshot
from ..models.outcomes import BundleOutcome


class ExecutiveSavingsDashboardEngine:
    """Aggregate outcome metrics for executive visibility."""

    def build_snapshot(self, outcomes: List[BundleOutcome]) -> ExecutiveSavingsSnapshot:
        shipment_total = sum(o.shipments_reduced or 0 for o in outcomes)
        outreach_total = sum(o.outreach_suppressed or 0 for o in outcomes)
        cost_total = sum(o.cost_savings_estimate or 0.0 for o in outcomes)
        return ExecutiveSavingsSnapshot(
            total_shipments_reduced=shipment_total,
            total_outreach_suppressed=outreach_total,
            total_cost_savings=cost_total,
            outcomes_tracked=len(outcomes),
            metadata={"average_savings_per_outcome": cost_total / len(outcomes) if outcomes else 0.0},
        )
