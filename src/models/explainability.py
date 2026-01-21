"""
Explainability Layer Data Models for PharmIQ

This module provides comprehensive data structures for explaining bundle risks,
including driver analysis, evidence presentation, and actionable insights.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator


class ExplanationType(str, Enum):
    """Types of explanations supported"""
    RISK_DRIVERS = "risk_drivers"
    EVIDENCE_SUMMARY = "evidence_summary"
    RECOMMENDATION_RATIONALE = "recommendation_rationale"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    HISTORICAL_CONTEXT = "historical_context"
    PREDICTIVE_INSIGHTS = "predictive_insights"


class DriverImpact(str, Enum):
    """Driver impact levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class EvidenceType(str, Enum):
    """Types of evidence supporting explanations"""
    METRIC_VALUE = "metric_value"
    THRESHOLD_COMPARISON = "threshold_comparison"
    HISTORICAL_PATTERN = "historical_pattern"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    CORRELATION_ANALYSIS = "correlation_analysis"
    TREND_ANALYSIS = "trend_analysis"


class VisualizationType(str, Enum):
    """Types of visualizations for explanations"""
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    SCATTER_PLOT = "scatter_plot"
    HEAT_MAP = "heat_map"
    TIMELINE = "timeline"
    NETWORK_GRAPH = "network_graph"
    GAUGE = "gauge"
    PROGRESS_BAR = "progress_bar"


class Evidence(BaseModel):
    """Individual evidence piece supporting an explanation"""
    evidence_id: str
    evidence_type: EvidenceType
    description: str
    value: Union[float, int, str]
    context: Dict[str, Any]
    confidence: float = Field(ge=0, le=1, description="Confidence in evidence (0-1)")
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RiskDriverExplanation(BaseModel):
    """Detailed explanation of a risk driver"""
    driver_id: str
    driver_name: str
    driver_type: str
    impact_level: DriverImpact
    impact_score: float = Field(ge=0, le=1, description="Impact score (0-1)")
    confidence: float = Field(ge=0, le=1, description="Confidence in driver assessment (0-1)")
    
    # Evidence supporting this driver
    evidence: List[Evidence]
    
    # Explanation components
    narrative: str
    key_insights: List[str]
    contributing_factors: List[str]
    
    # Comparative analysis
    benchmark_comparison: Optional[Dict[str, Any]] = None
    historical_trend: Optional[Dict[str, Any]] = None
    
    # Visualization data
    visualization_data: Optional[Dict[str, Any]] = None
    visualization_type: Optional[VisualizationType] = None
    
    # Mitigation context
    mitigation_potential: float = Field(ge=0, le=1, description="Potential for risk reduction (0-1)")
    mitigation_difficulty: str = Field(description="Difficulty of mitigation: easy, moderate, hard")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RecommendationExplanation(BaseModel):
    """Explanation for why a recommendation was generated"""
    recommendation_id: str
    recommendation_title: str
    recommendation_type: str
    priority: str
    
    # Rationale
    primary_rationale: str
    supporting_reasons: List[str]
    expected_outcome: str
    
    # Evidence base
    supporting_evidence: List[Evidence]
    success_probability: float = Field(ge=0, le=1, description="Probability of success (0-1)")
    
    # Implementation context
    implementation_complexity: str
    resource_requirements: List[str]
    time_to_impact: str
    
    # Cost-benefit analysis
    estimated_cost: Optional[float] = None
    estimated_savings: Optional[float] = None
    roi_estimate: Optional[float] = None
    
    # Risk reduction
    risk_reduction_potential: float = Field(ge=0, le=1, description="Potential risk reduction (0-1)")
    affected_drivers: List[str]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ComparativeAnalysis(BaseModel):
    """Comparative analysis of similar cases or benchmarks"""
    analysis_id: str
    comparison_type: str  # peer_comparison, historical_comparison, benchmark_comparison
    comparison_description: str
    
    # Reference group
    reference_group_size: int
    reference_group_description: str
    
    # Comparison metrics
    similarity_score: float = Field(ge=0, le=1, description="Similarity to reference group (0-1)")
    percentile_ranking: float = Field(ge=0, le=100, description="Percentile ranking in reference group")
    
    # Key differences
    key_differences: List[Dict[str, Any]]
    common_patterns: List[Dict[str, Any]]
    
    # Insights from comparison
    comparative_insights: List[str]
    learning_opportunities: List[str]
    
    # Visualization
    comparison_chart_data: Optional[Dict[str, Any]] = None
    distribution_data: Optional[Dict[str, Any]] = None


class HistoricalContext(BaseModel):
    """Historical context and trend analysis"""
    context_id: str
    time_period_start: datetime
    time_period_end: datetime
    analysis_period: str
    
    # Historical data
    historical_data_points: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    
    # Pattern recognition
    identified_patterns: List[Dict[str, Any]]
    seasonal_effects: Optional[Dict[str, Any]] = None
    cyclical_patterns: Optional[Dict[str, Any]] = None
    
    # Historical performance
    historical_risk_levels: List[Dict[str, Any]]
    intervention_effectiveness: Optional[Dict[str, Any]] = None
    
    # Predictions based on history
    historical_predictions: List[Dict[str, Any]]
    confidence_intervals: List[Dict[str, Any]]
    
    # Lessons learned
    historical_lessons: List[str]
    best_practices: List[str]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PredictiveInsights(BaseModel):
    """Predictive insights and forecasting"""
    insight_id: str
    prediction_type: str
    prediction_horizon: str
    
    # Predictions
    primary_prediction: str
    prediction_confidence: float = Field(ge=0, le=1, description="Confidence in prediction (0-1)")
    
    # Risk trajectory
    risk_trajectory: List[Dict[str, Any]]
    critical_timepoints: List[Dict[str, Any]]
    
    # Influencing factors
    key_influencing_factors: List[Dict[str, Any]]
    scenario_analysis: Dict[str, Any]
    
    # Early warning indicators
    early_warning_signals: List[Dict[str, Any]]
    monitoring_recommendations: List[str]
    
    # Intervention opportunities
    optimal_intervention_points: List[Dict[str, Any]]
    intervention_effectiveness: Dict[str, Any]
    
    # Visualization
    forecast_chart_data: Optional[Dict[str, Any]] = None
    confidence_bands: Optional[Dict[str, Any]] = None


class BundleRiskExplanation(BaseModel):
    """Comprehensive explanation for bundle risk assessment"""
    explanation_id: str
    bundle_id: str
    risk_type: str  # bundle_break, abandonment, shipment_split, fulfillment_delay
    risk_assessment_id: str
    
    # Overall explanation
    executive_summary: str
    detailed_explanation: str
    key_takeaways: List[str]
    
    # Driver explanations
    primary_drivers: List[RiskDriverExplanation]
    secondary_drivers: List[RiskDriverExplanation]
    
    # Recommendation explanations
    recommendation_explanations: List[RecommendationExplanation]
    
    # Contextual analysis
    comparative_analysis: Optional[ComparativeAnalysis] = None
    historical_context: Optional[HistoricalContext] = None
    predictive_insights: Optional[PredictiveInsights] = None
    
    # Overall metrics
    overall_confidence: float = Field(ge=0, le=1, description="Overall explanation confidence (0-1)")
    explanation_completeness: float = Field(ge=0, le=1, description="Completeness of explanation (0-1)")
    
    # Metadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    explanation_version: str = "1.0"
    model_version: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExplanationQuery(BaseModel):
    """Query parameters for explanation retrieval"""
    explanation_types: Optional[List[ExplanationType]] = None
    risk_types: Optional[List[str]] = None
    bundle_ids: Optional[List[str]] = None
    member_ids: Optional[List[str]] = None
    time_range: Optional[Dict[str, datetime]] = None
    confidence_threshold: Optional[float] = Field(ge=0, le=1, default=0.5)
    include_visualizations: bool = True
    include_historical: bool = True
    include_comparative: bool = True
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExplanationList(BaseModel):
    """List of explanations with pagination"""
    explanations: List[BundleRiskExplanation]
    total_count: int
    has_more: bool
    query_summary: Dict[str, Any]


class ExplanationVisualization(BaseModel):
    """Visualization data for explanations"""
    visualization_id: str
    explanation_id: str
    visualization_type: VisualizationType
    title: str
    description: str
    
    # Chart data
    chart_data: Dict[str, Any]
    chart_config: Dict[str, Any]
    
    # Interactive elements
    interactive_elements: Optional[List[Dict[str, Any]]] = None
    
    # Export options
    export_formats: List[str] = ["png", "svg", "pdf"]
    
    # Accessibility
    alt_text: str
    data_labels: bool = True
    color_scheme: str = "accessible"


class ExplanationReport(BaseModel):
    """Comprehensive explanation report"""
    report_id: str
    report_type: str  # bundle_risk, member_risk, operational_insights
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    time_period: Dict[str, datetime]
    
    # Report content
    executive_summary: str
    key_findings: List[str]
    detailed_analysis: List[BundleRiskExplanation]
    
    # Visualizations
    visualizations: List[ExplanationVisualization]
    
    # Recommendations
    prioritized_recommendations: List[RecommendationExplanation]
    
    # Appendices
    methodology: str
    assumptions: List[str]
    limitations: List[str]
    
    # Metadata
    data_sources: List[str]
    model_versions: Dict[str, str]
    confidence_levels: Dict[str, float]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExplainabilityConfig(BaseModel):
    """Configuration for explainability layer"""
    model_name: str = "bundle_risk_explainability"
    model_version: str = "1.0"
    
    # Explanation depth
    max_primary_drivers: int = Field(default=5, ge=1, le=10)
    max_secondary_drivers: int = Field(default=10, ge=1, le=20)
    max_evidence_per_driver: int = Field(default=5, ge=1, le=10)
    
    # Confidence thresholds
    min_driver_confidence: float = Field(default=0.3, ge=0, le=1)
    min_evidence_confidence: float = Field(default=0.5, ge=0, le=1)
    min_overall_confidence: float = Field(default=0.7, ge=0, le=1)
    
    # Visualization settings
    default_visualization_types: List[VisualizationType] = [
        VisualizationType.BAR_CHART,
        VisualizationType.LINE_CHART,
        VisualizationType.GAUGE
    ]
    
    # Historical analysis
    historical_lookback_days: int = Field(default=90, ge=7, le=365)
    min_historical_data_points: int = Field(default=10, ge=5, le=100)
    
    # Comparative analysis
    min_comparator_group_size: int = Field(default=5, ge=3, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0, le=1)
    
    # Report generation
    max_report_explanations: int = Field(default=20, ge=1, le=100)
    include_confidence_intervals: bool = True
    include_benchmark_comparisons: bool = True
