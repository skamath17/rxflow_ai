"""
Bundle Metrics Computation Engine for PharmIQ

This module implements the computation engine for bundle-relevant metrics
from refill snapshots. The engine transforms snapshot data into quantitative
metrics that support risk assessment and bundle intelligence.

The engine is designed to be:
- Deterministic (same snapshots produce same metrics)
- Efficient (optimized for batch processing)
- Extensible (supports custom metric computations)
- Explainable (clear metric definitions and calculations)
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import statistics

from ..models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState
from ..models.metrics import (
    BundleMetrics, BundleMetricsSummary, MetricsQuery, MetricsList,
    AgeInStageMetrics, TimingOverlapMetrics, RefillGapMetrics, BundleAlignmentMetrics,
    MetricSeverity, MetricType
)
from ..utils.audit import AuditLogger, AuditAction, AuditSeverity


class BundleMetricsEngine:
    """Engine for computing bundle-relevant metrics from refill snapshots"""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """Initialize bundle metrics engine"""
        self.audit_logger = audit_logger or AuditLogger()
        self._metrics_cache: Dict[str, BundleMetrics] = {}
        self._member_metrics_index: Dict[str, List[str]] = defaultdict(list)
        self._bundle_metrics_index: Dict[str, List[str]] = defaultdict(list)
        
        # Metric computation thresholds and parameters
        self._stage_age_thresholds = {
            SnapshotStage.INITIATED: 3,      # 3 days
            SnapshotStage.ELIGIBLE: 7,       # 7 days
            SnapshotStage.PA_PENDING: 5,     # 5 days
            SnapshotStage.PA_APPROVED: 3,    # 3 days
            SnapshotStage.BUNDLED: 2,        # 2 days
            SnapshotStage.OOS_DETECTED: 1,   # 1 day
            SnapshotStage.SHIPPED: 0,        # 0 days (completed)
            SnapshotStage.COMPLETED: 0,      # 0 days (completed)
        }
        
        self._risk_score_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.9
        }
    
    def compute_metrics(self, snapshot: RefillSnapshot, bundle_snapshots: Optional[List[RefillSnapshot]] = None) -> BundleMetrics:
        """Compute comprehensive bundle metrics for a snapshot"""
        start_time = time.time()
        
        # Get bundle context if available
        bundle_context = self._get_bundle_context(snapshot, bundle_snapshots)
        
        # Compute individual metric groups
        age_metrics = self._compute_age_in_stage_metrics(snapshot)
        timing_metrics = self._compute_timing_overlap_metrics(snapshot, bundle_context)
        gap_metrics = self._compute_refill_gap_metrics(snapshot)
        alignment_metrics = self._compute_bundle_alignment_metrics(snapshot, bundle_context)
        
        # Compute overall risk assessment
        risk_score, risk_severity, risk_factors = self._compute_overall_risk(
            age_metrics, timing_metrics, gap_metrics, alignment_metrics
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            age_metrics, timing_metrics, gap_metrics, alignment_metrics, risk_severity
        )
        
        # Create comprehensive metrics
        metrics = BundleMetrics(
            snapshot_id=snapshot.snapshot_id,
            member_id=snapshot.member_id,
            refill_id=snapshot.refill_id,
            computed_timestamp=datetime.now(timezone.utc),
            age_in_stage=age_metrics,
            timing_overlap=timing_metrics,
            refill_gap=gap_metrics,
            bundle_alignment=alignment_metrics,
            overall_risk_score=risk_score,
            risk_severity=risk_severity,
            primary_risk_factors=risk_factors,
            requires_attention=risk_severity in [MetricSeverity.HIGH, MetricSeverity.CRITICAL],
            recommended_actions=recommendations,
            computation_time_ms=int((time.time() - start_time) * 1000)
        )
        
        # Cache metrics
        self._metrics_cache[metrics.snapshot_id] = metrics
        self._member_metrics_index[metrics.member_id].append(metrics.snapshot_id)
        if snapshot.bundle_id:
            self._bundle_metrics_index[snapshot.bundle_id].append(metrics.snapshot_id)
        
        # Log computation
        self.audit_logger.log_metrics_computed(
            snapshot_id=snapshot.snapshot_id,
            member_id=snapshot.member_id,
            refill_id=snapshot.refill_id,
            risk_score=risk_score,
            computation_time_ms=metrics.computation_time_ms
        )
        
        return metrics
    
    def compute_batch_metrics(self, snapshots: List[RefillSnapshot]) -> List[BundleMetrics]:
        """Compute metrics for multiple snapshots"""
        metrics_list = []
        
        # Group snapshots by bundle for context
        bundle_groups = defaultdict(list)
        for snapshot in snapshots:
            if snapshot.bundle_id:
                bundle_groups[snapshot.bundle_id].append(snapshot)
        
        # Compute metrics for each snapshot
        for snapshot in snapshots:
            bundle_snapshots = bundle_groups.get(snapshot.bundle_id, [])
            metrics = self.compute_metrics(snapshot, bundle_snapshots)
            metrics_list.append(metrics)
        
        return metrics_list
    
    def get_metrics(self, snapshot_id: str) -> Optional[BundleMetrics]:
        """Retrieve computed metrics by snapshot ID"""
        return self._metrics_cache.get(snapshot_id)
    
    def query_metrics(self, query: MetricsQuery) -> MetricsList:
        """Query metrics based on criteria"""
        all_metrics = list(self._metrics_cache.values())
        
        # Apply filters
        filtered_metrics = self._apply_filters(all_metrics, query)
        
        # Sort results
        sorted_metrics = self._sort_metrics(filtered_metrics, query.sort_by, query.sort_order)
        
        # Paginate
        total_count = len(sorted_metrics)
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_metrics = sorted_metrics[start_idx:end_idx]
        
        # Generate summary
        summary = self._generate_summary(paginated_metrics) if paginated_metrics else None
        
        return MetricsList(
            metrics=paginated_metrics,
            total_count=total_count,
            limit=query.limit,
            offset=query.offset,
            has_more=end_idx < total_count,
            summary=summary
        )
    
    def get_member_metrics(self, member_id: str, limit: int = 100) -> List[BundleMetrics]:
        """Get all metrics for a member"""
        metric_ids = self._member_metrics_index.get(member_id, [])
        metrics = [self._metrics_cache[mid] for mid in metric_ids if mid in self._metrics_cache]
        
        # Sort by computation timestamp descending
        metrics.sort(key=lambda m: m.computed_timestamp, reverse=True)
        
        return metrics[:limit]
    
    def get_bundle_metrics(self, bundle_id: str, limit: int = 100) -> List[BundleMetrics]:
        """Get all metrics for a bundle"""
        metric_ids = self._bundle_metrics_index.get(bundle_id, [])
        metrics = [self._metrics_cache[mid] for mid in metric_ids if mid in self._metrics_cache]
        
        # Sort by computation timestamp descending
        metrics.sort(key=lambda m: m.computed_timestamp, reverse=True)
        
        return metrics[:limit]
    
    def _compute_age_in_stage_metrics(self, snapshot: RefillSnapshot) -> AgeInStageMetrics:
        """Compute age-in-stage metrics"""
        current_stage = snapshot.current_stage
        
        # Build stage history from timestamps
        stage_history = {}
        if snapshot.initiated_timestamp:
            end_time = snapshot.eligible_timestamp or snapshot.snapshot_timestamp
            stage_history["initiated"] = (end_time - snapshot.initiated_timestamp).days
        if snapshot.eligible_timestamp:
            end_time = snapshot.pa_submitted_timestamp or snapshot.bundled_timestamp or snapshot.snapshot_timestamp
            stage_history["eligible"] = (end_time - snapshot.eligible_timestamp).days
        if snapshot.pa_submitted_timestamp:
            end_time = snapshot.pa_resolved_timestamp or snapshot.snapshot_timestamp
            stage_history["pa_submitted"] = (end_time - snapshot.pa_submitted_timestamp).days
        if snapshot.pa_resolved_timestamp:
            end_time = snapshot.bundled_timestamp or snapshot.shipped_timestamp or snapshot.snapshot_timestamp
            stage_history["pa_resolved"] = (end_time - snapshot.pa_resolved_timestamp).days
        if snapshot.bundled_timestamp:
            end_time = snapshot.shipped_timestamp or snapshot.snapshot_timestamp
            stage_history["bundled"] = (end_time - snapshot.bundled_timestamp).days
        if snapshot.shipped_timestamp:
            end_time = snapshot.completed_timestamp or snapshot.snapshot_timestamp
            stage_history["shipped"] = (end_time - snapshot.shipped_timestamp).days
        
        # Compute stage transition times
        initiation_to_eligible = None
        eligibility_to_bundled = None
        bundled_to_shipped = None
        
        if snapshot.initiated_timestamp and snapshot.eligible_timestamp:
            initiation_to_eligible = (snapshot.eligible_timestamp - snapshot.initiated_timestamp).days
        if snapshot.eligible_timestamp and snapshot.bundled_timestamp:
            eligibility_to_bundled = (snapshot.bundled_timestamp - snapshot.eligible_timestamp).days
        if snapshot.bundled_timestamp and snapshot.shipped_timestamp:
            bundled_to_shipped = (snapshot.shipped_timestamp - snapshot.bundled_timestamp).days
        
        # Determine if aging in stage
        threshold = self._stage_age_thresholds.get(current_stage, 3)
        is_aging = snapshot.days_in_current_stage > threshold
        
        return AgeInStageMetrics(
            current_stage=current_stage.value,
            days_in_current_stage=snapshot.days_in_current_stage or 0,
            stage_history=stage_history,
            initiation_to_eligible_days=initiation_to_eligible,
            eligibility_to_bundled_days=eligibility_to_bundled,
            bundled_to_shipped_days=bundled_to_shipped,
            is_aging_in_stage=is_aging,
            stage_age_percentile=self._compute_stage_age_percentile(snapshot.days_in_current_stage or 0, current_stage)
        )
    
    def _compute_timing_overlap_metrics(self, snapshot: RefillSnapshot, bundle_context: Dict[str, Any]) -> TimingOverlapMetrics:
        """Compute timing overlap metrics"""
        bundle_id = snapshot.bundle_id
        bundle_size = bundle_context.get("bundle_size", 1)
        
        if bundle_size <= 1:
            # Single refill bundle
            return TimingOverlapMetrics(
                bundle_id=bundle_id,
                bundle_size=bundle_size,
                refill_overlap_score=1.0,
                timing_variance_days=0.0,
                max_timing_gap_days=0,
                is_well_aligned=True,
                alignment_efficiency=1.0,
                fragmentation_risk=0.0,
                shipment_split_probability=0.0
            )
        
        # Compute overlap metrics for multi-refill bundles
        bundle_snapshots = bundle_context.get("snapshots", [])
        refill_due_dates = [s.refill_due_date for s in bundle_snapshots if s.refill_due_date]
        
        if len(refill_due_dates) < 2:
            # Insufficient data for overlap analysis
            return TimingOverlapMetrics(
                bundle_id=bundle_id,
                bundle_size=bundle_size,
                refill_overlap_score=0.5,
                timing_variance_days=30.0,
                max_timing_gap_days=30,
                is_well_aligned=False,
                alignment_efficiency=0.5,
                fragmentation_risk=0.5,
                shipment_split_probability=0.5
            )
        
        # Calculate timing variance
        timing_gaps = []
        for i in range(len(refill_due_dates) - 1):
            gap = abs((refill_due_dates[i+1] - refill_due_dates[i]).days)
            timing_gaps.append(gap)
        
        timing_variance = statistics.variance(timing_gaps) if len(timing_gaps) > 1 else 0
        max_gap = max(timing_gaps) if timing_gaps else 0
        
        # Compute overlap score (inverse of variance)
        overlap_score = max(0, 1 - (timing_variance / 900))  # Normalize by 30-day variance
        
        # Compute alignment efficiency
        alignment_efficiency = 1.0 - (max_gap / 30.0)  # Penalty for large gaps
        alignment_efficiency = max(0, alignment_efficiency)
        
        # Risk calculations
        fragmentation_risk = min(1.0, max_gap / 14.0)  # Risk increases with gaps > 14 days
        shipment_split_probability = fragmentation_risk * 0.8  # High correlation
        
        return TimingOverlapMetrics(
            bundle_id=bundle_id,
            bundle_size=bundle_size,
            refill_overlap_score=overlap_score,
            timing_variance_days=timing_variance,
            max_timing_gap_days=max_gap,
            is_well_aligned=alignment_efficiency > 0.8,
            alignment_efficiency=alignment_efficiency,
            fragmentation_risk=fragmentation_risk,
            shipment_split_probability=shipment_split_probability
        )
    
    def _compute_refill_gap_metrics(self, snapshot: RefillSnapshot) -> RefillGapMetrics:
        """Compute refill gap metrics"""
        days_since_last_fill = snapshot.days_since_last_fill or 0
        days_until_due = snapshot.days_until_due or 0
        
        # Compute refill gap
        refill_gap = days_since_last_fill
        
        # Determine optimal gap (typically 30 days for most medications)
        optimal_gap = 30
        gap_efficiency = 1.0 - abs(refill_gap - optimal_gap) / optimal_gap
        gap_efficiency = max(0, gap_efficiency)
        
        is_optimal = abs(refill_gap - optimal_gap) <= 7  # Within 7 days of optimal
        
        # Risk calculations
        abandonment_risk = 0.0
        if days_since_last_fill > 90:
            abandonment_risk = min(1.0, (days_since_last_fill - 90) / 90)
        elif days_since_last_fill > 60:
            abandonment_risk = min(0.5, (days_since_last_fill - 60) / 60)
        
        # Urgency based on days until due
        urgency_score = 0.0
        if days_until_due < 0:
            urgency_score = 1.0  # Overdue
        elif days_until_due < 7:
            urgency_score = 0.8  # Very urgent
        elif days_until_due < 14:
            urgency_score = 0.5  # Urgent
        elif days_until_due < 30:
            urgency_score = 0.2  # Moderate urgency
        
        # Supply calculations
        days_supply_remaining = None
        supply_buffer_days = None
        
        if snapshot.days_supply and snapshot.last_fill_date:
            days_consumed = (datetime.now(timezone.utc).date() - snapshot.last_fill_date.date()).days
            days_supply_remaining = max(0, snapshot.days_supply - days_consumed)
            supply_buffer_days = days_supply_remaining - days_until_due
        
        return RefillGapMetrics(
            days_since_last_fill=days_since_last_fill,
            days_until_next_due=days_until_due,
            refill_gap_days=refill_gap,
            is_optimal_gap=is_optimal,
            gap_efficiency_score=gap_efficiency,
            abandonment_risk=abandonment_risk,
            urgency_score=urgency_score,
            days_supply_remaining=days_supply_remaining,
            supply_buffer_days=supply_buffer_days
        )
    
    def _compute_bundle_alignment_metrics(self, snapshot: RefillSnapshot, bundle_context: Dict[str, Any]) -> BundleAlignmentMetrics:
        """Compute bundle alignment metrics"""
        bundle_id = snapshot.bundle_id
        bundle_member_count = bundle_context.get("bundle_member_count", 1)
        bundle_refill_count = bundle_context.get("bundle_refill_count", 1)
        
        # Use existing bundle alignment score from snapshot
        bundle_alignment_score = snapshot.bundle_alignment_score or 0.5
        
        # Compute timing alignment
        timing_alignment = bundle_alignment_score  # Simplified for now
        
        # Compute bundle efficiency
        bundle_efficiency = bundle_alignment_score * 0.8  # Adjust for real-world factors
        
        # Cost savings potential (simplified calculation)
        cost_savings = min(1.0, bundle_refill_count * 0.1)  # More refills = more savings
        
        # Risk calculations
        split_risk = 1.0 - bundle_alignment_score  # Inverse relationship
        
        # Outreach reduction potential
        outreach_reduction = bundle_efficiency * 0.7
        
        # Overall bundle health
        bundle_health = (bundle_alignment_score + bundle_efficiency + cost_savings) / 3
        
        # Generate recommendations
        recommended_actions = []
        if bundle_alignment_score < 0.6:
            recommended_actions.append("Review bundle timing alignment")
        if bundle_efficiency < 0.5:
            recommended_actions.append("Optimize bundle composition")
        if split_risk > 0.7:
            recommended_actions.append("Monitor for potential shipment splits")
        
        return BundleAlignmentMetrics(
            bundle_id=bundle_id,
            bundle_member_count=bundle_member_count,
            bundle_refill_count=bundle_refill_count,
            bundle_alignment_score=bundle_alignment_score,
            timing_alignment_score=timing_alignment,
            geographic_alignment_score=None,  # Not implemented yet
            bundle_efficiency_score=bundle_efficiency,
            cost_savings_potential=cost_savings,
            split_risk_score=split_risk,
            outreach_reduction_score=outreach_reduction,
            bundle_health_score=bundle_health,
            recommended_actions=recommended_actions
        )
    
    def _compute_overall_risk(self, age_metrics: AgeInStageMetrics, timing_metrics: TimingOverlapMetrics,
                           gap_metrics: RefillGapMetrics, alignment_metrics: BundleAlignmentMetrics) -> Tuple[float, MetricSeverity, List[str]]:
        """Compute overall risk assessment"""
        risk_factors = []
        risk_scores = []
        
        # Age-in-stage risk
        if age_metrics.is_aging_in_stage:
            age_risk = min(1.0, age_metrics.days_in_current_stage / 14.0)
            risk_scores.append(age_risk * 0.3)
            risk_factors.append(f"Aging in {age_metrics.current_stage} stage")
        
        # Timing overlap risk
        risk_scores.append(timing_metrics.fragmentation_risk * 0.4)
        if timing_metrics.fragmentation_risk > 0.6:
            risk_factors.append("Bundle fragmentation risk")
        
        # Refill gap risk
        risk_scores.append(gap_metrics.abandonment_risk * 0.3)
        if gap_metrics.abandonment_risk > 0.5:
            risk_factors.append("Refill abandonment risk")
        
        # Bundle alignment risk
        risk_scores.append(alignment_metrics.split_risk_score * 0.2)
        if alignment_metrics.split_risk_score > 0.7:
            risk_factors.append("Bundle split risk")
        
        # Compute overall risk score
        overall_risk = sum(risk_scores) if risk_scores else 0.0
        overall_risk = min(1.0, overall_risk)
        
        # Determine severity
        if overall_risk >= self._risk_score_thresholds["critical"]:
            severity = MetricSeverity.CRITICAL
        elif overall_risk >= self._risk_score_thresholds["high"]:
            severity = MetricSeverity.HIGH
        elif overall_risk >= self._risk_score_thresholds["medium"]:
            severity = MetricSeverity.MEDIUM
        else:
            severity = MetricSeverity.LOW
        
        return overall_risk, severity, risk_factors
    
    def _generate_recommendations(self, age_metrics: AgeInStageMetrics, timing_metrics: TimingOverlapMetrics,
                                gap_metrics: RefillGapMetrics, alignment_metrics: BundleAlignmentMetrics,
                                severity: MetricSeverity) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Age-based recommendations
        if age_metrics.is_aging_in_stage:
            recommendations.append(f"Expedite {age_metrics.current_stage} processing")
        
        # Timing-based recommendations
        if not timing_metrics.is_well_aligned:
            recommendations.append("Review bundle timing coordination")
        
        # Gap-based recommendations
        if gap_metrics.urgency_score > 0.7:
            recommendations.append("Prioritize refill processing")
        
        # Alignment-based recommendations
        if alignment_metrics.bundle_health_score < 0.5:
            recommendations.append("Review bundle composition")
        
        # Severity-based recommendations
        if severity == MetricSeverity.CRITICAL:
            recommendations.insert(0, "IMMEDIATE ATTENTION REQUIRED")
        elif severity == MetricSeverity.HIGH:
            recommendations.insert(0, "High priority - review within 24 hours")
        
        return recommendations
    
    def _get_bundle_context(self, snapshot: RefillSnapshot, bundle_snapshots: Optional[List[RefillSnapshot]]) -> Dict[str, Any]:
        """Get bundle context for metrics computation"""
        if not snapshot.bundle_id:
            return {
                "bundle_size": 1,
                "bundle_member_count": 1,
                "bundle_refill_count": 1,
                "snapshots": [snapshot]
            }
        
        # Use provided bundle snapshots or return empty list
        if bundle_snapshots is None:
            bundle_snapshots = []
        
        return {
            "bundle_size": len(bundle_snapshots),
            "bundle_member_count": len(set(s.member_id for s in bundle_snapshots)),
            "bundle_refill_count": len(bundle_snapshots),
            "snapshots": bundle_snapshots
        }
    
    def _compute_stage_age_percentile(self, days_in_stage: int, stage: SnapshotStage) -> Optional[float]:
        """Compute percentile for stage age (simplified)"""
        # This would typically use historical data
        # For now, use a simple heuristic
        threshold = self._stage_age_thresholds.get(stage, 3)
        return min(1.0, days_in_stage / (threshold * 2))
    
    def _apply_filters(self, metrics: List[BundleMetrics], query: MetricsQuery) -> List[BundleMetrics]:
        """Apply query filters to metrics"""
        filtered = metrics
        
        if query.member_id:
            filtered = [m for m in filtered if m.member_id == query.member_id]
        
        if query.refill_id:
            filtered = [m for m in filtered if m.refill_id == query.refill_id]
        
        if query.bundle_id:
            filtered = [m for m in filtered if m.bundle_alignment.bundle_id == query.bundle_id]
        
        if query.min_risk_score is not None:
            filtered = [m for m in filtered if m.overall_risk_score >= query.min_risk_score]
        
        if query.max_risk_score is not None:
            filtered = [m for m in filtered if m.overall_risk_score <= query.max_risk_score]
        
        if query.risk_severity:
            filtered = [m for m in filtered if m.risk_severity == query.risk_severity]
        
        if query.computed_timestamp_from:
            filtered = [m for m in filtered if m.computed_timestamp >= query.computed_timestamp_from]
        
        if query.computed_timestamp_to:
            filtered = [m for m in filtered if m.computed_timestamp <= query.computed_timestamp_to]
        
        return filtered
    
    def _sort_metrics(self, metrics: List[BundleMetrics], sort_by: str, sort_order: str) -> List[BundleMetrics]:
        """Sort metrics by specified field"""
        reverse = sort_order.lower() == "desc"
        
        if sort_by == "computed_timestamp":
            return sorted(metrics, key=lambda m: m.computed_timestamp, reverse=reverse)
        elif sort_by == "overall_risk_score":
            return sorted(metrics, key=lambda m: m.overall_risk_score, reverse=reverse)
        elif sort_by == "risk_severity":
            severity_order = [MetricSeverity.LOW, MetricSeverity.MEDIUM, MetricSeverity.HIGH, MetricSeverity.CRITICAL]
            return sorted(metrics, key=lambda m: severity_order.index(m.risk_severity), reverse=reverse)
        else:
            # Default sort by computed timestamp
            return sorted(metrics, key=lambda m: m.computed_timestamp, reverse=reverse)
    
    def _generate_summary(self, metrics: List[BundleMetrics]) -> BundleMetricsSummary:
        """Generate summary statistics for metrics"""
        if not metrics:
            return BundleMetricsSummary(
                computed_timestamp=datetime.now(timezone.utc),
                total_snapshots=0,
                avg_risk_score=0.0,
                high_risk_count=0,
                critical_risk_count=0,
                stage_distribution={},
                avg_bundle_health=0.0,
                total_bundles=0,
                computation_time_ms=0
            )
        
        # Calculate aggregates
        total_snapshots = len(metrics)
        avg_risk_score = sum(m.overall_risk_score for m in metrics) / total_snapshots
        high_risk_count = sum(1 for m in metrics if m.risk_severity == MetricSeverity.HIGH)
        critical_risk_count = sum(1 for m in metrics if m.risk_severity == MetricSeverity.CRITICAL)
        
        # Stage distribution
        stage_dist = defaultdict(int)
        for m in metrics:
            stage_dist[m.age_in_stage.current_stage] += 1
        
        # Bundle health
        avg_bundle_health = sum(m.bundle_alignment.bundle_health_score for m in metrics) / total_snapshots
        total_bundles = len(set(m.bundle_alignment.bundle_id for m in metrics if m.bundle_alignment.bundle_id))
        
        return BundleMetricsSummary(
            computed_timestamp=datetime.now(timezone.utc),
            total_snapshots=total_snapshots,
            avg_risk_score=avg_risk_score,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            stage_distribution=dict(stage_dist),
            avg_bundle_health=avg_bundle_health,
            total_bundles=total_bundles,
            computation_time_ms=sum(m.computation_time_ms for m in metrics)
        )
