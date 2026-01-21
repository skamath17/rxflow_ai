"""
Bundle Metrics Module for PharmIQ

This module provides bundle-relevant metrics computation that transforms
refill snapshots into quantitative indicators for risk assessment and
bundle intelligence.

Key components:
- BundleMetricsEngine: Core metrics computation engine
- Bundle metrics models: Data structures for metrics
- Integration with snapshot aggregation system
"""

from .bundle_metrics_engine import BundleMetricsEngine

__all__ = ["BundleMetricsEngine"]
