"""
Bundle Risk Scoring Module for PharmIQ

This module provides explainable risk scoring that detects bundle
fragmentation and refill abandonment risk. The risk models build on
bundle metrics to provide predictive intelligence for bundle preservation.

Key components:
- BundleRiskScoringEngine: Core risk scoring engine
- Risk models: Data structures for risk assessments
- Explainability layer: Clear drivers and recommendations
- Integration with bundle metrics system
"""

from .risk_scoring_engine import BundleRiskScoringEngine

__all__ = ["BundleRiskScoringEngine"]
