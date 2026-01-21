"""
Refill Snapshot Aggregation Module for PharmIQ

This module provides snapshot aggregation capabilities that transform streams of
canonical events into comprehensive refill state snapshots. These snapshots
serve as the foundation for risk scoring and bundle intelligence.

Key components:
- SnapshotEngine: Core aggregation engine
- Snapshot models: Data structures for snapshots
- Integration with event processing pipeline
"""

from .snapshot_engine import SnapshotAggregationEngine

__all__ = ["SnapshotAggregationEngine"]
