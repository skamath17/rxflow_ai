"""
Bundle Risk Scoring Models for PharmIQ

This module defines the data structures for explainable risk scoring
that detects bundle fragmentation and refill abandonment risk. The risk models
are designed to be:

- Explainable: Clear drivers and evidence for risk scores
- Actionable: Specific recommendations for risk mitigation
- Auditable: Complete traceability of risk assessments
- Configurable: Adjustable thresholds and weights

The risk models build on the bundle metrics foundation to provide
predictive risk intelligence for bundle preservation and outreach optimization.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator


class RiskType(str, Enum):
    """Types of risk that can be assessed"""
    BUNDLE_BREAK = "bundle_break"
    REFILL_ABANDONMENT = "refill_abandonment"
    SHIPMENT_SPLIT = "shipment_split"
    FULFILLMENT_DELAY = "fulfillment_delay"
    OUTREACH_WASTE = "outreach_waste"


class RiskSeverity(str, Enum):
    """Risk severity levels with business meaning"""
    LOW = "low"           # < 30% probability, routine monitoring
    MEDIUM = "medium"     # 30-60% probability, proactive attention
    HIGH = "high"         # 60-80% probability, immediate action
    CRITICAL = "critical" # > 80% probability, urgent intervention


class RiskDriverType(str, Enum):
    """Types of risk drivers that explain risk scores"""
    TIMING_MISALIGNMENT = "timing_misalignment"
    PA_PROCESSING_DELAY = "pa_processing_delay"
    OOS_DISRUPTION = "oos_disruption"
    STAGE_AGING = "stage_aging"
    BUNDLE_FRAGMENTATION = "bundle_fragmentation"
    REFILL_GAP_ANOMALY = "refill_gap_anomaly"
    SUPPLY_BUFFER_DEPLETION = "supply_buffer_depletion"
    MEMBER_BEHAVIOR_CHANGE = "member_behavior_change"
    EXTERNAL_SYSTEM_DELAY = "external_system_delay"


class RiskDriver(BaseModel):
    """Individual risk driver with evidence and impact"""
    
    driver_type: RiskDriverType = Field(..., description="Type of risk driver")
    driver_name: str = Field(..., description="Human-readable driver name")
    impact_score: float = Field(..., description="Impact on overall risk score (0-1)")
    confidence: float = Field(..., description="Confidence in driver assessment (0-1)")
    
    # Evidence and context
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    metric_values: Dict[str, float] = Field(default_factory=dict, description="Relevant metric values")
    
    # Temporal context
    detected_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trend_direction: Optional[str] = Field(None, description="Trend direction (improving/worsening/stable)")
    
    @validator('impact_score', 'confidence')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class RiskRecommendation(BaseModel):
    """Actionable recommendation for risk mitigation"""
    
    recommendation_id: str = Field(..., description="Unique recommendation identifier")
    priority: str = Field(..., description="Priority level (urgent/high/medium/low)")
    category: str = Field(..., description="Recommendation category")
    
    # Recommendation content
    title: str = Field(..., description="Brief recommendation title")
    description: str = Field(..., description="Detailed recommendation description")
    action_steps: List[str] = Field(default_factory=list, description="Specific action steps")
    
    # Expected outcomes
    expected_impact: str = Field(..., description="Expected impact if implemented")
    time_to_implement: str = Field(..., description="Estimated time to implement")
    success_probability: Optional[float] = Field(None, description="Probability of success (0-1)")
    
    # Context
    applicable_stages: List[str] = Field(default_factory=list, description="Applicable lifecycle stages")
    required_resources: List[str] = Field(default_factory=list, description="Resources needed")
    
    @validator('success_probability')
    def validate_probability(cls, v):
        """Validate probability is between 0 and 1"""
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Probability must be between 0 and 1")
        return v


class BundleBreakRisk(BaseModel):
    """Bundle break risk assessment"""
    
    # Risk identification
    risk_id: str = Field(..., description="Unique risk assessment identifier")
    bundle_id: str = Field(..., description="Bundle identifier")
    assessment_timestamp: datetime = Field(..., description="Risk assessment timestamp")
    model_version: str = Field("1.0", description="Risk model version")
    
    # Risk scores
    break_probability: float = Field(..., description="Probability of bundle break (0-1)")
    break_severity: RiskSeverity = Field(..., description="Risk severity level")
    confidence_score: float = Field(..., description="Confidence in assessment (0-1)")
    
    # Risk drivers
    primary_drivers: List[RiskDriver] = Field(default_factory=list, description="Primary risk drivers")
    secondary_drivers: List[RiskDriver] = Field(default_factory=list, description="Secondary risk drivers")
    
    # Bundle context
    bundle_size: int = Field(..., description="Number of refills in bundle")
    bundle_health_score: float = Field(..., description="Overall bundle health (0-1)")
    timing_alignment_score: float = Field(..., description="Timing alignment (0-1)")
    
    # Risk timeline
    estimated_break_timeframe: Optional[str] = Field(None, description="Estimated timeframe for break")
    critical_factors: List[str] = Field(default_factory=list, description="Critical factors to monitor")
    
    # Recommendations
    recommendations: List[RiskRecommendation] = Field(default_factory=list, description="Risk mitigation recommendations")
    
    @validator('break_probability', 'confidence_score', 'bundle_health_score', 'timing_alignment_score')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class RefillAbandonmentRisk(BaseModel):
    """Refill abandonment risk assessment"""
    
    # Risk identification
    risk_id: str = Field(..., description="Unique risk assessment identifier")
    refill_id: str = Field(..., description="Refill identifier")
    member_id: str = Field(..., description="Member identifier")
    assessment_timestamp: datetime = Field(..., description="Risk assessment timestamp")
    model_version: str = Field("1.0", description="Risk model version")
    
    # Risk scores
    abandonment_probability: float = Field(..., description="Probability of abandonment (0-1)")
    abandonment_severity: RiskSeverity = Field(..., description="Risk severity level")
    confidence_score: float = Field(..., description="Confidence in assessment (0-1)")
    
    # Risk drivers
    primary_drivers: List[RiskDriver] = Field(default_factory=list, description="Primary risk drivers")
    secondary_drivers: List[RiskDriver] = Field(default_factory=list, description="Secondary risk drivers")
    
    # Refill context
    days_since_last_fill: int = Field(..., description="Days since last fill")
    days_until_due: int = Field(..., description="Days until next due date")
    refill_stage: str = Field(..., description="Current refill stage")
    
    # Behavioral indicators
    engagement_score: Optional[float] = Field(None, description="Member engagement score (0-1)")
    compliance_history: Dict[str, Any] = Field(default_factory=dict, description="Historical compliance data")
    
    # Risk timeline
    estimated_abandonment_timeframe: Optional[str] = Field(None, description="Estimated timeframe for abandonment")
    critical_factors: List[str] = Field(default_factory=list, description="Critical factors to monitor")
    
    # Recommendations
    recommendations: List[RiskRecommendation] = Field(default_factory=list, description="Risk mitigation recommendations")
    
    @validator('abandonment_probability', 'confidence_score', 'engagement_score')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class RiskAssessmentSummary(BaseModel):
    """Summary of risk assessments across multiple entities"""
    
    # Assessment metadata
    assessment_timestamp: datetime = Field(..., description="Assessment timestamp")
    model_version: str = Field("1.0", description="Risk model version")
    total_assessments: int = Field(..., description="Total number of assessments")
    
    # Risk distribution
    risk_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution by risk type")
    severity_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution by severity")
    
    # Aggregate metrics
    avg_break_probability: float = Field(..., description="Average bundle break probability")
    avg_abandonment_probability: float = Field(..., description="Average abandonment probability")
    high_risk_count: int = Field(..., description="Number of high/critical risk assessments")
    
    # Performance metrics
    assessment_time_ms: int = Field(..., description="Total assessment time (milliseconds)")
    
    @validator('avg_break_probability', 'avg_abandonment_probability')
    def validate_averages(cls, v):
        """Validate averages are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Averages must be between 0 and 1")
        return v


class RiskQuery(BaseModel):
    """Query parameters for risk assessments"""
    
    # Entity filters
    risk_type: Optional[RiskType] = Field(None, description="Filter by risk type")
    bundle_id: Optional[str] = Field(None, description="Filter by bundle ID")
    member_id: Optional[str] = Field(None, description="Filter by member ID")
    refill_id: Optional[str] = Field(None, description="Filter by refill ID")
    
    # Risk filters
    min_probability: Optional[float] = Field(None, description="Minimum probability threshold")
    max_probability: Optional[float] = Field(None, description="Maximum probability threshold")
    severity: Optional[RiskSeverity] = Field(None, description="Filter by severity level")
    
    # Time filters
    assessment_timestamp_from: Optional[datetime] = Field(None, description="Assessment timestamp from")
    assessment_timestamp_to: Optional[datetime] = Field(None, description="Assessment timestamp to")
    
    # Pagination
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")
    
    # Sorting
    sort_by: str = Field("assessment_timestamp", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


class RiskList(BaseModel):
    """Response model for risk assessment queries"""
    
    risks: List[Union[BundleBreakRisk, RefillAbandonmentRisk]] = Field(..., description="List of risk assessments")
    total_count: int = Field(..., description="Total number of risk assessments matching query")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")
    has_more: bool = Field(..., description="Whether more results are available")
    
    # Summary statistics
    summary: Optional[RiskAssessmentSummary] = Field(None, description="Summary statistics")


class RiskModelConfig(BaseModel):
    """Configuration for risk scoring models"""
    
    # Model parameters
    model_name: str = Field(..., description="Model name")
    model_version: str = Field("1.0", description="Model version")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Thresholds
    break_risk_thresholds: Dict[str, float] = Field(
        default={
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        },
        description="Break risk probability thresholds"
    )
    
    abandonment_risk_thresholds: Dict[str, float] = Field(
        default={
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        },
        description="Abandonment risk probability thresholds"
    )
    
    # Driver weights
    driver_weights: Dict[str, float] = Field(
        default={
            "timing_misalignment": 0.3,
            "pa_processing_delay": 0.25,
            "oos_disruption": 0.2,
            "stage_aging": 0.15,
            "bundle_fragmentation": 0.1
        },
        description="Weights for different risk drivers"
    )
    
    # Confidence thresholds
    min_confidence_threshold: float = Field(0.7, description="Minimum confidence for risk assessment")
    
    @validator('break_risk_thresholds', 'abandonment_risk_thresholds')
    def validate_thresholds(cls, v):
        """Validate threshold values"""
        for key, value in v.items():
            if not 0 <= value <= 1:
                raise ValueError(f"Threshold {key} must be between 0 and 1")
        return v
    
    @validator('driver_weights')
    def validate_weights(cls, v):
        """Validate weight values sum to 1.0"""
        total_weight = sum(v.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small rounding errors
            raise ValueError(f"Driver weights must sum to 1.0, got {total_weight}")
        return v
