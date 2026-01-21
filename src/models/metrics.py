"""
Bundle-Relevant Snapshot Metrics for PharmIQ

This module defines the metrics computed from refill snapshots that are
relevant for bundle risk assessment and intelligence. These metrics
provide the quantitative foundation for risk scoring and explainability.

Metrics are designed to be:
- Bundle-relevant (focused on bundle dynamics)
- Time-aware (consider temporal patterns)
- Risk-indicative (predictive of bundle issues)
- Explainable (clear business meaning)
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class MetricType(str, Enum):
    """Types of bundle-relevant metrics"""
    AGE_IN_STAGE = "age_in_stage"
    TIMING_OVERLAP = "timing_overlap"
    REFILL_GAP = "refill_gap"
    BUNDLE_ALIGNMENT = "bundle_alignment"
    PROCESSING_DELAY = "processing_delay"
    BUNDLE_EFFICIENCY = "bundle_efficiency"
    SPLIT_RISK = "split_risk"


class MetricSeverity(str, Enum):
    """Severity levels for metric values"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgeInStageMetrics(BaseModel):
    """Metrics related to how long refills spend in each lifecycle stage"""
    
    # Current stage metrics
    current_stage: str = Field(..., description="Current lifecycle stage")
    days_in_current_stage: int = Field(..., description="Days spent in current stage")
    
    # Historical stage metrics
    stage_history: Dict[str, int] = Field(default_factory=dict, description="Days spent in each stage")
    
    # Stage-specific metrics
    initiation_to_eligible_days: Optional[int] = Field(None, description="Days from initiation to eligibility")
    eligibility_to_bundled_days: Optional[int] = Field(None, description="Days from eligibility to bundling")
    bundled_to_shipped_days: Optional[int] = Field(None, description="Days from bundling to shipment")
    
    # Age indicators
    is_aging_in_stage: bool = Field(..., description="Whether refill is aging in current stage")
    stage_age_percentile: Optional[float] = Field(None, description="Percentile for stage age")
    
    @validator('days_in_current_stage')
    def validate_days_in_stage(cls, v):
        """Validate days in stage is non-negative"""
        if v < 0:
            raise ValueError("Days in stage cannot be negative")
        return v


class TimingOverlapMetrics(BaseModel):
    """Metrics related to timing overlaps between refills in bundles"""
    
    # Bundle timing context
    bundle_id: Optional[str] = Field(None, description="Bundle identifier")
    bundle_size: int = Field(..., description="Number of refills in bundle")
    
    # Overlap metrics
    refill_overlap_score: float = Field(..., description="Timing overlap score (0-1)")
    timing_variance_days: float = Field(..., description="Variance in refill timing (days)")
    max_timing_gap_days: int = Field(..., description="Maximum timing gap between refills")
    
    # Alignment indicators
    is_well_aligned: bool = Field(..., description="Whether refills are well-aligned")
    alignment_efficiency: float = Field(..., description="Bundle alignment efficiency (0-1)")
    
    # Risk indicators
    fragmentation_risk: float = Field(..., description="Risk of bundle fragmentation (0-1)")
    shipment_split_probability: float = Field(..., description="Probability of shipment split (0-1)")
    
    @validator('refill_overlap_score', 'alignment_efficiency', 'fragmentation_risk', 'shipment_split_probability')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class RefillGapMetrics(BaseModel):
    """Metrics related to gaps between refill events"""
    
    # Gap measurements
    days_since_last_fill: int = Field(..., description="Days since last fill")
    days_until_next_due: int = Field(..., description="Days until next due date")
    refill_gap_days: int = Field(..., description="Gap between refills")
    
    # Gap analysis
    is_optimal_gap: bool = Field(..., description="Whether gap is optimal")
    gap_efficiency_score: float = Field(..., description="Gap efficiency score (0-1)")
    
    # Risk indicators
    abandonment_risk: float = Field(..., description="Risk of abandonment (0-1)")
    urgency_score: float = Field(..., description="Refill urgency score (0-1)")
    
    # Supply considerations
    days_supply_remaining: Optional[int] = Field(None, description="Days of supply remaining")
    supply_buffer_days: Optional[int] = Field(None, description="Supply buffer in days")
    
    @validator('gap_efficiency_score', 'abandonment_risk', 'urgency_score')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class BundleAlignmentMetrics(BaseModel):
    """Metrics related to bundle alignment and timing"""
    
    # Bundle context
    bundle_id: Optional[str] = Field(None, description="Bundle identifier")
    bundle_member_count: int = Field(..., description="Number of members in bundle")
    bundle_refill_count: int = Field(..., description="Number of refills in bundle")
    
    # Alignment scores
    bundle_alignment_score: float = Field(..., description="Overall bundle alignment (0-1)")
    timing_alignment_score: float = Field(..., description="Timing alignment (0-1)")
    geographic_alignment_score: Optional[float] = Field(None, description="Geographic alignment (0-1)")
    
    # Bundle efficiency
    bundle_efficiency_score: float = Field(..., description="Bundle efficiency (0-1)")
    cost_savings_potential: float = Field(..., description="Potential cost savings (0-1)")
    
    # Risk indicators
    split_risk_score: float = Field(..., description="Bundle split risk (0-1)")
    outreach_reduction_score: float = Field(..., description="Outreach reduction potential (0-1)")
    
    # Bundle health indicators
    bundle_health_score: float = Field(..., description="Overall bundle health (0-1)")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    
    @validator('bundle_alignment_score', 'timing_alignment_score', 'bundle_efficiency_score', 
               'cost_savings_potential', 'split_risk_score', 'outreach_reduction_score', 'bundle_health_score')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class BundleMetrics(BaseModel):
    """Comprehensive bundle-relevant metrics for a refill snapshot"""
    
    # Metadata
    snapshot_id: str = Field(..., description="Source snapshot ID")
    member_id: str = Field(..., description="Member identifier")
    refill_id: str = Field(..., description="Refill identifier")
    computed_timestamp: datetime = Field(..., description="Metrics computation timestamp")
    metrics_version: str = Field("1.0", description="Metrics schema version")
    
    # Core metric groups
    age_in_stage: AgeInStageMetrics = Field(..., description="Age-in-stage metrics")
    timing_overlap: TimingOverlapMetrics = Field(..., description="Timing overlap metrics")
    refill_gap: RefillGapMetrics = Field(..., description="Refill gap metrics")
    bundle_alignment: BundleAlignmentMetrics = Field(..., description="Bundle alignment metrics")
    
    # Overall risk assessment
    overall_risk_score: float = Field(..., description="Overall bundle risk score (0-1)")
    risk_severity: MetricSeverity = Field(..., description="Risk severity level")
    primary_risk_factors: List[str] = Field(default_factory=list, description="Primary risk factors")
    
    # Actionability
    requires_attention: bool = Field(..., description="Whether attention is required")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    
    # Performance metrics
    computation_time_ms: int = Field(..., description="Time to compute metrics (milliseconds)")
    
    @validator('overall_risk_score')
    def validate_risk_score(cls, v):
        """Validate risk score is between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Risk score must be between 0 and 1")
        return v


class BundleMetricsSummary(BaseModel):
    """Summary of metrics across multiple snapshots"""
    
    # Summary metadata
    computed_timestamp: datetime = Field(..., description="Summary computation timestamp")
    total_snapshots: int = Field(..., description="Number of snapshots analyzed")
    metrics_version: str = Field("1.0", description="Metrics schema version")
    
    # Aggregate metrics
    avg_risk_score: float = Field(..., description="Average risk score")
    high_risk_count: int = Field(..., description="Number of high-risk snapshots")
    critical_risk_count: int = Field(..., description="Number of critical-risk snapshots")
    
    # Stage distribution
    stage_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution by stage")
    
    # Bundle health
    avg_bundle_health: float = Field(..., description="Average bundle health score")
    total_bundles: int = Field(..., description="Total number of bundles")
    
    # Performance metrics
    computation_time_ms: int = Field(..., description="Total computation time (milliseconds)")
    
    @validator('avg_risk_score', 'avg_bundle_health')
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class MetricsQuery(BaseModel):
    """Query parameters for metrics retrieval"""
    
    # Identifier filters
    member_id: Optional[str] = Field(None, description="Filter by member ID")
    refill_id: Optional[str] = Field(None, description="Filter by refill ID")
    bundle_id: Optional[str] = Field(None, description="Filter by bundle ID")
    
    # Risk filters
    min_risk_score: Optional[float] = Field(None, description="Minimum risk score")
    max_risk_score: Optional[float] = Field(None, description="Maximum risk score")
    risk_severity: Optional[MetricSeverity] = Field(None, description="Risk severity filter")
    
    # Timing filters
    computed_timestamp_from: Optional[datetime] = Field(None, description="Computation timestamp from")
    computed_timestamp_to: Optional[datetime] = Field(None, description="Computation timestamp to")
    
    # Pagination
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")
    
    # Sorting
    sort_by: str = Field("computed_timestamp", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


class MetricsList(BaseModel):
    """Response model for metrics list queries"""
    
    metrics: List[BundleMetrics] = Field(..., description="List of bundle metrics")
    total_count: int = Field(..., description="Total number of metrics matching query")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")
    has_more: bool = Field(..., description="Whether more results are available")
    
    # Summary statistics
    summary: Optional[BundleMetricsSummary] = Field(None, description="Summary statistics")
