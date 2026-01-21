"""
Bundle Risk Scoring Engine for PharmIQ

This module implements explainable risk scoring models that detect bundle
fragmentation and refill abandonment risk. The engine uses bundle metrics
to compute risk scores with clear drivers and actionable recommendations.

The engine is designed to be:
- Explainable: Clear drivers and evidence for risk scores
- Actionable: Specific recommendations for risk mitigation
- Auditable: Complete traceability of risk assessments
- Configurable: Adjustable thresholds and weights
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict
import statistics

from ..models.snapshots import RefillSnapshot, SnapshotStage, PAState, BundleTimingState
from ..models.metrics import BundleMetrics
from ..models.risk import (
    BundleBreakRisk, RefillAbandonmentRisk, RiskAssessmentSummary, RiskQuery, RiskList,
    RiskType, RiskSeverity, RiskDriverType, RiskDriver, RiskRecommendation,
    RiskModelConfig
)
from ..utils.audit import AuditLogger, AuditAction, AuditSeverity
from ..utils.version_registry import VersionRegistry
from ..models.versioning import VersionedArtifactType


class BundleRiskScoringEngine:
    """Engine for computing explainable bundle risk scores"""
    
    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        config: Optional[RiskModelConfig] = None,
        version_registry: Optional[VersionRegistry] = None,
    ):
        """Initialize risk scoring engine"""
        self.audit_logger = audit_logger or AuditLogger()
        self.config = config or RiskModelConfig(model_name="bundle_risk_engine_v1")
        self.version_registry = version_registry or VersionRegistry()
        
        # Risk assessment storage
        self._risk_cache: Dict[str, Union[BundleBreakRisk, RefillAbandonmentRisk]] = {}
        self._bundle_risk_index: Dict[str, List[str]] = defaultdict(list)
        self._member_risk_index: Dict[str, List[str]] = defaultdict(list)
        
        # Risk scoring thresholds and weights
        self._initialize_scoring_parameters()
    
    def _initialize_scoring_parameters(self):
        """Initialize scoring parameters from config"""
        self.break_thresholds = self.config.break_risk_thresholds
        self.abandonment_thresholds = self.config.abandonment_risk_thresholds
        self.driver_weights = self.config.driver_weights
        self.min_confidence = self.config.min_confidence_threshold
    
    def assess_bundle_break_risk(self, metrics: BundleMetrics, bundle_snapshots: Optional[List[BundleMetrics]] = None) -> BundleBreakRisk:
        """Assess bundle break risk with explainable drivers"""
        start_time = time.time()
        
        # Generate risk ID
        risk_id = f"bundle_break_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Compute break probability
        break_probability = self._compute_break_probability(metrics, bundle_snapshots)
        
        # Determine severity
        severity = self._determine_risk_severity(break_probability, self.break_thresholds)
        
        # Identify risk drivers
        primary_drivers, secondary_drivers = self._identify_bundle_break_drivers(metrics, bundle_snapshots)
        
        # Compute confidence
        confidence = self._compute_assessment_confidence(metrics, primary_drivers)
        
        # Generate recommendations
        recommendations = self._generate_bundle_break_recommendations(metrics, primary_drivers, severity)
        
        # Create risk assessment
        risk_assessment = BundleBreakRisk(
            risk_id=risk_id,
            bundle_id=metrics.bundle_alignment.bundle_id or "unknown",
            assessment_timestamp=datetime.now(timezone.utc),
            model_version=self.config.model_version,
            break_probability=break_probability,
            break_severity=severity,
            confidence_score=confidence,
            primary_drivers=primary_drivers,
            secondary_drivers=secondary_drivers,
            bundle_size=metrics.bundle_alignment.bundle_refill_count,
            bundle_health_score=metrics.bundle_alignment.bundle_health_score,
            timing_alignment_score=metrics.bundle_alignment.timing_alignment_score,
            estimated_break_timeframe=self._estimate_break_timeframe(metrics, primary_drivers),
            critical_factors=self._identify_critical_factors(primary_drivers),
            recommendations=recommendations
        )
        
        # Cache and index
        self._risk_cache[risk_id] = risk_assessment
        if risk_assessment.bundle_id != "unknown":
            self._bundle_risk_index[risk_assessment.bundle_id].append(risk_id)
        
        # Log assessment
        assessment_time_ms = int((time.time() - start_time) * 1000)
        self.audit_logger.log_risk_assessment(
            risk_id=risk_id,
            risk_type="bundle_break",
            entity_id=risk_assessment.bundle_id,
            probability=break_probability,
            severity=severity.value,
            assessment_time_ms=assessment_time_ms
        )

        self.version_registry.register(
            artifact_id=risk_id,
            artifact_type=VersionedArtifactType.RISK_ASSESSMENT,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            metadata={"risk_type": RiskType.BUNDLE_BREAK.value},
        )
        
        return risk_assessment
    
    def assess_abandonment_risk(self, metrics: BundleMetrics, snapshot: Optional[RefillSnapshot] = None) -> RefillAbandonmentRisk:
        """Assess refill abandonment risk with explainable drivers"""
        start_time = time.time()
        
        # Generate risk ID
        risk_id = f"abandonment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Compute abandonment probability
        abandonment_probability = self._compute_abandonment_probability(metrics, snapshot)
        
        # Determine severity
        severity = self._determine_risk_severity(abandonment_probability, self.abandonment_thresholds)
        
        # Identify risk drivers
        primary_drivers, secondary_drivers = self._identify_abandonment_drivers(metrics, snapshot)
        
        # Compute confidence
        confidence = self._compute_assessment_confidence(metrics, primary_drivers)
        
        # Generate recommendations
        recommendations = self._generate_abandonment_recommendations(metrics, primary_drivers, severity)
        
        # Create risk assessment
        risk_assessment = RefillAbandonmentRisk(
            risk_id=risk_id,
            refill_id=metrics.refill_id,
            member_id=metrics.member_id,
            assessment_timestamp=datetime.now(timezone.utc),
            model_version=self.config.model_version,
            abandonment_probability=abandonment_probability,
            abandonment_severity=severity,
            confidence_score=confidence,
            primary_drivers=primary_drivers,
            secondary_drivers=secondary_drivers,
            days_since_last_fill=metrics.refill_gap.days_since_last_fill,
            days_until_due=metrics.refill_gap.days_until_next_due,
            refill_stage=metrics.age_in_stage.current_stage,
            engagement_score=self._compute_engagement_score(metrics),
            compliance_history=self._extract_compliance_history(metrics),
            estimated_abandonment_timeframe=self._estimate_abandonment_timeframe(metrics, primary_drivers),
            critical_factors=self._identify_critical_factors(primary_drivers),
            recommendations=recommendations
        )
        
        # Cache and index
        self._risk_cache[risk_id] = risk_assessment
        self._member_risk_index[risk_assessment.member_id].append(risk_id)
        
        # Log assessment
        assessment_time_ms = int((time.time() - start_time) * 1000)
        self.audit_logger.log_risk_assessment(
            risk_id=risk_id,
            risk_type="refill_abandonment",
            entity_id=risk_assessment.refill_id,
            probability=abandonment_probability,
            severity=severity.value,
            assessment_time_ms=assessment_time_ms
        )

        self.version_registry.register(
            artifact_id=risk_id,
            artifact_type=VersionedArtifactType.RISK_ASSESSMENT,
            model_name=self.config.model_name,
            model_version=self.config.model_version,
            metadata={"risk_type": RiskType.REFILL_ABANDONMENT.value},
        )
        
        return risk_assessment
    
    def assess_batch_risks(self, metrics_list: List[BundleMetrics], snapshots: Optional[List[RefillSnapshot]] = None) -> List[Union[BundleBreakRisk, RefillAbandonmentRisk]]:
        """Assess risks for multiple metrics"""
        risk_assessments = []
        
        # Group metrics by bundle for batch processing
        bundle_groups = defaultdict(list)
        for metrics in metrics_list:
            bundle_id = metrics.bundle_alignment.bundle_id
            if bundle_id:
                bundle_groups[bundle_id].append(metrics)
            else:
                # Single refill - assess abandonment risk only
                risk = self.assess_abandonment_risk(metrics)
                risk_assessments.append(risk)
        
        # Assess bundle break risks for multi-refill bundles
        for bundle_id, bundle_metrics in bundle_groups.items():
            if len(bundle_metrics) > 1:
                # Assess bundle break risk for the bundle
                primary_metrics = bundle_metrics[0]  # Use first metric as representative
                bundle_risk = self.assess_bundle_break_risk(primary_metrics, bundle_metrics)
                risk_assessments.append(bundle_risk)
                
                # Assess abandonment risk for individual refills
                for metrics in bundle_metrics:
                    abandonment_risk = self.assess_abandonment_risk(metrics)
                    risk_assessments.append(abandonment_risk)
        
        return risk_assessments
    
    def get_risk_assessment(self, risk_id: str) -> Optional[Union[BundleBreakRisk, RefillAbandonmentRisk]]:
        """Retrieve a risk assessment by ID"""
        return self._risk_cache.get(risk_id)
    
    def query_risk_assessments(self, query: RiskQuery) -> RiskList:
        """Query risk assessments based on criteria"""
        all_risks = list(self._risk_cache.values())
        
        # Apply filters
        filtered_risks = self._apply_risk_filters(all_risks, query)
        
        # Sort results
        sorted_risks = self._sort_risk_assessments(filtered_risks, query.sort_by, query.sort_order)
        
        # Paginate
        total_count = len(sorted_risks)
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_risks = sorted_risks[start_idx:end_idx]
        
        # Generate summary
        summary = self._generate_risk_summary(paginated_risks) if paginated_risks else None
        
        return RiskList(
            risks=paginated_risks,
            total_count=total_count,
            limit=query.limit,
            offset=query.offset,
            has_more=end_idx < total_count,
            summary=summary
        )
    
    def get_bundle_risks(self, bundle_id: str, limit: int = 100) -> List[BundleBreakRisk]:
        """Get all risk assessments for a bundle"""
        risk_ids = self._bundle_risk_index.get(bundle_id, [])
        risks = [self._risk_cache[rid] for rid in risk_ids if rid in self._risk_cache]
        bundle_risks = [r for r in risks if isinstance(r, BundleBreakRisk)]
        
        # Sort by assessment timestamp descending
        bundle_risks.sort(key=lambda r: r.assessment_timestamp, reverse=True)
        
        return bundle_risks[:limit]
    
    def get_member_risks(self, member_id: str, limit: int = 100) -> List[RefillAbandonmentRisk]:
        """Get all risk assessments for a member"""
        risk_ids = self._member_risk_index.get(member_id, [])
        risks = [self._risk_cache[rid] for rid in risk_ids if rid in self._risk_cache]
        member_risks = [r for r in risks if isinstance(r, RefillAbandonmentRisk)]
        
        # Sort by assessment timestamp descending
        member_risks.sort(key=lambda r: r.assessment_timestamp, reverse=True)
        
        return member_risks[:limit]
    
    def _compute_break_probability(self, metrics: BundleMetrics, bundle_snapshots: Optional[List[BundleMetrics]]) -> float:
        """Compute bundle break probability using weighted driver scores"""
        driver_scores = []
        
        # Timing misalignment driver
        timing_score = 1.0 - metrics.bundle_alignment.timing_alignment_score
        driver_scores.append(("timing_misalignment", timing_score))
        
        # Bundle fragmentation driver
        fragmentation_score = metrics.timing_overlap.fragmentation_risk
        driver_scores.append(("bundle_fragmentation", fragmentation_score))
        
        # Stage aging driver
        aging_score = self._compute_stage_aging_risk(metrics)
        driver_scores.append(("stage_aging", aging_score))
        
        # Bundle health driver
        health_score = 1.0 - metrics.bundle_alignment.bundle_health_score
        driver_scores.append(("bundle_health", health_score))
        
        # PA processing driver (if applicable)
        pa_score = self._compute_pa_processing_risk(metrics)
        if pa_score > 0:
            driver_scores.append(("pa_processing_delay", pa_score))
        
        # OOS disruption driver (if applicable)
        oos_score = self._compute_oos_disruption_risk(metrics)
        if oos_score > 0:
            driver_scores.append(("oos_disruption", oos_score))
        
        # Compute weighted probability
        weighted_score = sum(self.driver_weights.get(driver_type, 0) * score 
                           for driver_type, score in driver_scores)
        
        return min(1.0, max(0.0, weighted_score))
    
    def _compute_abandonment_probability(self, metrics: BundleMetrics, snapshot: Optional[RefillSnapshot]) -> float:
        """Compute refill abandonment probability"""
        driver_scores = []
        
        # Refill gap driver
        gap_score = metrics.refill_gap.abandonment_risk
        driver_scores.append(("refill_gap_anomaly", gap_score))
        
        # Urgency driver
        urgency_score = metrics.refill_gap.urgency_score
        driver_scores.append(("supply_buffer_depletion", urgency_score))
        
        # Stage aging driver
        aging_score = self._compute_stage_aging_risk(metrics)
        driver_scores.append(("stage_aging", aging_score))
        
        # Engagement driver (simplified)
        engagement_score = self._compute_engagement_risk(metrics)
        driver_scores.append(("member_behavior_change", engagement_score))
        
        # Bundle context driver
        bundle_score = self._compute_bundle_context_risk(metrics)
        if bundle_score > 0:
            driver_scores.append(("bundle_fragmentation", bundle_score))
        
        # Compute weighted probability
        weighted_score = sum(self.driver_weights.get(driver_type, 0) * score 
                           for driver_type, score in driver_scores)
        
        return min(1.0, max(0.0, weighted_score))
    
    def _determine_risk_severity(self, probability: float, thresholds: Dict[str, float]) -> RiskSeverity:
        """Determine risk severity from probability and thresholds"""
        if probability >= thresholds["high"]:
            return RiskSeverity.CRITICAL
        elif probability >= thresholds["medium"]:
            return RiskSeverity.HIGH
        elif probability >= thresholds["low"]:
            return RiskSeverity.MEDIUM
        else:
            return RiskSeverity.LOW
    
    def _identify_bundle_break_drivers(self, metrics: BundleMetrics, bundle_snapshots: Optional[List[BundleMetrics]]) -> Tuple[List[RiskDriver], List[RiskDriver]]:
        """Identify primary and secondary bundle break risk drivers"""
        drivers = []
        
        # Timing misalignment driver
        if metrics.bundle_alignment.timing_alignment_score < 0.7:
            impact = 1.0 - metrics.bundle_alignment.timing_alignment_score
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.TIMING_MISALIGNMENT,
                driver_name="Bundle Timing Misalignment",
                impact_score=impact,
                confidence=0.9,
                evidence={
                    "timing_alignment_score": metrics.bundle_alignment.timing_alignment_score,
                    "max_timing_gap": metrics.timing_overlap.max_timing_gap_days
                },
                metric_values={
                    "timing_alignment_score": metrics.bundle_alignment.timing_alignment_score,
                    "refill_overlap_score": metrics.timing_overlap.refill_overlap_score
                }
            ))
        
        # Bundle fragmentation driver
        if metrics.timing_overlap.fragmentation_risk > 0.5:
            impact = metrics.timing_overlap.fragmentation_risk
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.BUNDLE_FRAGMENTATION,
                driver_name="Bundle Fragmentation Risk",
                impact_score=impact,
                confidence=0.8,
                evidence={
                    "fragmentation_risk": metrics.timing_overlap.fragmentation_risk,
                    "shipment_split_probability": metrics.timing_overlap.shipment_split_probability
                },
                metric_values={
                    "fragmentation_risk": metrics.timing_overlap.fragmentation_risk,
                    "alignment_efficiency": metrics.timing_overlap.alignment_efficiency
                }
            ))
        
        # Stage aging driver
        aging_risk = self._compute_stage_aging_risk(metrics)
        if aging_risk > 0.6:
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.STAGE_AGING,
                driver_name="Stage Aging Risk",
                impact_score=aging_risk,
                confidence=0.7,
                evidence={
                    "days_in_current_stage": metrics.age_in_stage.days_in_current_stage,
                    "current_stage": metrics.age_in_stage.current_stage
                },
                metric_values={
                    "days_in_current_stage": metrics.age_in_stage.days_in_current_stage,
                    "stage_age_percentile": metrics.age_in_stage.stage_age_percentile
                }
            ))
        
        # Bundle health driver
        if metrics.bundle_alignment.bundle_health_score < 0.5:
            impact = 1.0 - metrics.bundle_alignment.bundle_health_score
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.BUNDLE_FRAGMENTATION,
                driver_name="Poor Bundle Health",
                impact_score=impact,
                confidence=0.6,
                evidence={
                    "bundle_health_score": metrics.bundle_alignment.bundle_health_score,
                    "bundle_efficiency_score": metrics.bundle_alignment.bundle_efficiency_score
                },
                metric_values={
                    "bundle_health_score": metrics.bundle_alignment.bundle_health_score,
                    "bundle_efficiency_score": metrics.bundle_alignment.bundle_efficiency_score
                }
            ))
        
        # Sort by impact and separate primary/secondary
        drivers.sort(key=lambda d: d.impact_score, reverse=True)
        primary_drivers = drivers[:2]  # Top 2 as primary
        secondary_drivers = drivers[2:]  # Rest as secondary
        
        return primary_drivers, secondary_drivers
    
    def _identify_abandonment_drivers(self, metrics: BundleMetrics, snapshot: Optional[RefillSnapshot]) -> Tuple[List[RiskDriver], List[RiskDriver]]:
        """Identify primary and secondary abandonment risk drivers"""
        drivers = []
        
        # Refill gap anomaly driver
        if metrics.refill_gap.abandonment_risk > 0.4:
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.REFILL_GAP_ANOMALY,
                driver_name="Refill Gap Anomaly",
                impact_score=metrics.refill_gap.abandonment_risk,
                confidence=0.9,
                evidence={
                    "days_since_last_fill": metrics.refill_gap.days_since_last_fill,
                    "days_until_next_due": metrics.refill_gap.days_until_next_due,
                    "gap_efficiency_score": metrics.refill_gap.gap_efficiency_score
                },
                metric_values={
                    "abandonment_risk": metrics.refill_gap.abandonment_risk,
                    "urgency_score": metrics.refill_gap.urgency_score,
                    "gap_efficiency_score": metrics.refill_gap.gap_efficiency_score
                }
            ))
        
        # Supply buffer depletion driver
        if metrics.refill_gap.urgency_score > 0.7:
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.SUPPLY_BUFFER_DEPLETION,
                driver_name="Supply Buffer Depletion",
                impact_score=metrics.refill_gap.urgency_score,
                confidence=0.8,
                evidence={
                    "days_supply_remaining": metrics.refill_gap.days_supply_remaining,
                    "supply_buffer_days": metrics.refill_gap.supply_buffer_days
                },
                metric_values={
                    "urgency_score": metrics.refill_gap.urgency_score,
                    "days_supply_remaining": metrics.refill_gap.days_supply_remaining
                }
            ))
        
        # Stage aging driver
        aging_risk = self._compute_stage_aging_risk(metrics)
        if aging_risk > 0.5:
            drivers.append(RiskDriver(
                driver_type=RiskDriverType.STAGE_AGING,
                driver_name="Stage Aging Risk",
                impact_score=aging_risk,
                confidence=0.7,
                evidence={
                    "days_in_current_stage": metrics.age_in_stage.days_in_current_stage,
                    "current_stage": metrics.age_in_stage.current_stage
                },
                metric_values={
                    "days_in_current_stage": metrics.age_in_stage.days_in_current_stage,
                    "stage_age_percentile": metrics.age_in_stage.stage_age_percentile
                }
            ))
        
        # Sort by impact and separate primary/secondary
        drivers.sort(key=lambda d: d.impact_score, reverse=True)
        primary_drivers = drivers[:2]  # Top 2 as primary
        secondary_drivers = drivers[2:]  # Rest as secondary
        
        return primary_drivers, secondary_drivers
    
    def _compute_assessment_confidence(self, metrics: BundleMetrics, drivers: List[RiskDriver]) -> float:
        """Compute confidence in risk assessment"""
        if not drivers:
            return 0.5  # Low confidence without drivers
        
        # Base confidence from driver confidence levels
        driver_confidence = statistics.mean([d.confidence for d in drivers])
        
        # Adjust based on data quality
        data_quality_factor = self._assess_data_quality(metrics)
        
        # Combine confidence factors
        confidence = driver_confidence * data_quality_factor
        
        return min(1.0, max(0.0, confidence))
    
    def _generate_bundle_break_recommendations(self, metrics: BundleMetrics, drivers: List[RiskDriver], severity: RiskSeverity) -> List[RiskRecommendation]:
        """Generate actionable recommendations for bundle break risk"""
        recommendations = []
        
        # Timing alignment recommendations
        timing_driver = next((d for d in drivers if d.driver_type == RiskDriverType.TIMING_MISALIGNMENT), None)
        if timing_driver and timing_driver.impact_score > 0.6:
            recommendations.append(RiskRecommendation(
                recommendation_id=f"timing_alignment_{uuid.uuid4().hex[:8]}",
                priority="high" if severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL] else "medium",
                category="timing_optimization",
                title="Optimize Bundle Timing Alignment",
                description="Improve timing coordination between refills to reduce fragmentation risk",
                action_steps=[
                    "Review refill due dates for bundle members",
                    "Adjust timing windows for better alignment",
                    "Coordinate with pharmacy for synchronized processing"
                ],
                expected_impact="Reduce bundle fragmentation risk by 30-50%",
                time_to_implement="1-2 weeks",
                success_probability=0.8,
                applicable_stages=["eligible", "bundled"],
                required_resources=["Pharmacy coordinator", "Scheduling system"]
            ))
        
        # Fragmentation risk recommendations
        fragmentation_driver = next((d for d in drivers if d.driver_type == RiskDriverType.BUNDLE_FRAGMENTATION), None)
        if fragmentation_driver and fragmentation_driver.impact_score > 0.5:
            recommendations.append(RiskRecommendation(
                recommendation_id=f"fragmentation_{uuid.uuid4().hex[:8]}",
                priority="high" if severity == RiskSeverity.CRITICAL else "medium",
                category="bundle_optimization",
                title="Address Bundle Fragmentation Risk",
                description="Take proactive steps to prevent bundle fragmentation",
                action_steps=[
                    "Identify root causes of timing misalignment",
                    "Implement bundle preservation strategies",
                    "Monitor fragmentation risk indicators"
                ],
                expected_impact="Prevent shipment splits and reduce costs",
                time_to_implement="2-4 weeks",
                success_probability=0.7,
                applicable_stages=["bundled", "shipped"],
                required_resources=["Bundle optimization team", "Analytics tools"]
            ))
        
        # Stage aging recommendations
        aging_driver = next((d for d in drivers if d.driver_type == RiskDriverType.STAGE_AGING), None)
        if aging_driver and aging_driver.impact_score > 0.6:
            recommendations.append(RiskRecommendation(
                recommendation_id=f"stage_aging_{uuid.uuid4().hex[:8]}",
                priority="high" if severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL] else "medium",
                category="process_optimization",
                title="Expedite Aging Refill Processing",
                description="Reduce processing time for refills stuck in current stage",
                action_steps=[
                    "Identify bottlenecks in current stage",
                    "Assign dedicated resources for stuck refills",
                    "Implement automated escalation for aging cases"
                ],
                expected_impact="Reduce abandonment risk and improve bundle integrity",
                time_to_implement="1 week",
                success_probability=0.9,
                applicable_stages=["initiated", "eligible", "pa_pending", "pa_approved"],
                required_resources=["Process improvement team", "Automation tools"]
            ))
        
        return recommendations
    
    def _generate_abandonment_recommendations(self, metrics: BundleMetrics, drivers: List[RiskDriver], severity: RiskSeverity) -> List[RiskRecommendation]:
        """Generate actionable recommendations for abandonment risk"""
        recommendations = []
        
        # Gap anomaly recommendations
        gap_driver = next((d for d in drivers if d.driver_type == RiskDriverType.REFILL_GAP_ANOMALY), None)
        if gap_driver and gap_driver.impact_score > 0.6:
            recommendations.append(RiskRecommendation(
                recommendation_id=f"gap_anomaly_{uuid.uuid4().hex[:8]}",
                priority="high" if severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL] else "medium",
                category="member_engagement",
                title="Address Refill Gap Anomaly",
                description="Proactive outreach to prevent refill abandonment",
                action_steps=[
                    "Contact member for refill confirmation",
                    "Offer convenient refill options",
                    "Provide education on adherence importance"
                ],
                expected_impact="Reduce abandonment risk by 40-60%",
                time_to_implement="2-3 days",
                success_probability=0.8,
                applicable_stages=["eligible", "bundled"],
                required_resources=["Care coordinator", "Outreach team"]
            ))
        
        # Supply buffer recommendations
        supply_driver = next((d for d in drivers if d.driver_type == RiskDriverType.SUPPLY_BUFFER_DEPLETION), None)
        if supply_driver and supply_driver.impact_score > 0.7:
            recommendations.append(RiskRecommendation(
                recommendation_id=f"supply_buffer_{uuid.uuid4().hex[:8]}",
                priority="high" if severity == RiskSeverity.CRITICAL else "medium",
                category="supply_management",
                title="Address Supply Buffer Depletion",
                description="Ensure adequate medication supply to prevent interruption",
                action_steps=[
                    "Check inventory levels for prescribed medication",
                    "Arrange early refill if supply is low",
                    "Provide temporary supply options if needed"
                ],
                expected_impact="Prevent treatment interruption",
                time_to_implement="3-5 days",
                success_probability=0.9,
                applicable_stages=["eligible", "bundled", "shipped"],
                required_resources=["Pharmacy staff", "Inventory system"]
            ))
        
        return recommendations
    
    def _compute_stage_aging_risk(self, metrics: BundleMetrics) -> float:
        """Compute risk from stage aging"""
        # Normalize stage age to 0-1 scale
        max_age_days = {
            "initiated": 7,
            "eligible": 14,
            "pa_pending": 10,
            "pa_approved": 7,
            "bundled": 5,
            "oos_detected": 3,
            "shipped": 0,
            "completed": 0
        }
        
        current_stage = metrics.age_in_stage.current_stage
        days_in_stage = metrics.age_in_stage.days_in_current_stage
        max_days = max_age_days.get(current_stage, 7)
        
        return min(1.0, days_in_stage / max_days)
    
    def _compute_pa_processing_risk(self, metrics: BundleMetrics) -> float:
        """Compute risk from PA processing delays"""
        if metrics.age_in_stage.current_stage in ["pa_pending", "pa_approved"]:
            return self._compute_stage_aging_risk(metrics)
        return 0.0
    
    def _compute_oos_disruption_risk(self, metrics: BundleMetrics) -> float:
        """Compute risk from OOS disruptions"""
        # Simplified OOS risk calculation
        if metrics.age_in_stage.current_stage == "oos_detected":
            return 0.8  # High risk when OOS detected
        return 0.0
    
    def _compute_engagement_score(self, metrics: BundleMetrics) -> float:
        """Compute member engagement score (simplified)"""
        # Base engagement from refill gap efficiency
        base_engagement = metrics.refill_gap.gap_efficiency_score
        
        # Adjust based on stage aging (longer aging = lower engagement)
        aging_penalty = self._compute_stage_aging_risk(metrics) * 0.3
        
        return max(0.0, base_engagement - aging_penalty)
    
    def _compute_engagement_risk(self, metrics: BundleMetrics) -> float:
        """Compute engagement risk (inverse of engagement score)"""
        return 1.0 - self._compute_engagement_score(metrics)
    
    def _compute_bundle_context_risk(self, metrics: BundleMetrics) -> float:
        """Compute risk from bundle context"""
        if metrics.bundle_alignment.bundle_refill_count <= 1:
            return 0.0  # Single refill, no bundle context risk
        
        # Risk increases with bundle fragmentation
        return metrics.timing_overlap.fragmentation_risk * 0.5
    
    def _estimate_break_timeframe(self, metrics: BundleMetrics, drivers: List[RiskDriver]) -> Optional[str]:
        """Estimate timeframe for potential bundle break"""
        # Use stage aging as primary indicator
        days_in_stage = metrics.age_in_stage.days_in_current_stage
        
        if days_in_stage > 14:
            return "2-4 weeks"
        elif days_in_stage > 7:
            return "1-2 weeks"
        elif days_in_stage > 3:
            return "1 week"
        else:
            return "3-7 days"
    
    def _estimate_abandonment_timeframe(self, metrics: BundleMetrics, drivers: List[RiskDriver]) -> Optional[str]:
        """Estimate timeframe for potential abandonment"""
        # Use days until due as primary indicator
        days_until_due = metrics.refill_gap.days_until_next_due
        
        if days_until_due < 0:
            return "Immediate (overdue)"
        elif days_until_due < 7:
            return "1 week"
        elif days_until_due < 14:
            return "1-2 weeks"
        elif days_until_due < 30:
            return "2-4 weeks"
        else:
            return "1+ months"
    
    def _identify_critical_factors(self, drivers: List[RiskDriver]) -> List[str]:
        """Identify critical factors to monitor"""
        factors = []
        
        for driver in drivers:
            if driver.driver_type == RiskDriverType.TIMING_MISALIGNMENT:
                factors.append("Timing alignment score")
                factors.append("Maximum timing gap")
            elif driver.driver_type == RiskDriverType.BUNDLE_FRAGMENTATION:
                factors.append("Fragmentation risk score")
                factors.append("Shipment split probability")
            elif driver.driver_type == RiskDriverType.STAGE_AGING:
                factors.append(f"Days in {driver.evidence.get('current_stage', 'unknown')} stage")
            elif driver.driver_type == RiskDriverType.REFILL_GAP_ANOMALY:
                factors.append("Days since last fill")
                factors.append("Days until next due")
            elif driver.driver_type == RiskDriverType.SUPPLY_BUFFER_DEPLETION:
                factors.append("Days supply remaining")
                factors.append("Supply buffer days")
        
        return factors
    
    def _extract_compliance_history(self, metrics: BundleMetrics) -> Dict[str, Any]:
        """Extract compliance history from metrics (simplified)"""
        return {
            "refill_events": metrics.refill_events,
            "pa_events": metrics.pa_events,
            "total_events": metrics.total_events,
            "last_activity": metrics.computed_timestamp.isoformat()
        }
    
    def _assess_data_quality(self, metrics: BundleMetrics) -> float:
        """Assess data quality for confidence calculation"""
        quality_score = 1.0
        
        # Reduce confidence if critical metrics are missing
        if metrics.bundle_alignment.bundle_alignment_score is None:
            quality_score -= 0.3
        if metrics.refill_gap.days_since_last_fill == 0:
            quality_score -= 0.2
        if metrics.age_in_stage.days_in_current_stage == 0:
            quality_score -= 0.2
        
        return max(0.1, quality_score)
    
    def _apply_risk_filters(self, risks: List[Union[BundleBreakRisk, RefillAbandonmentRisk]], query: RiskQuery) -> List[Union[BundleBreakRisk, RefillAbandonmentRisk]]:
        """Apply query filters to risk assessments"""
        filtered = risks
        
        if query.risk_type:
            if query.risk_type == RiskType.BUNDLE_BREAK:
                filtered = [r for r in filtered if isinstance(r, BundleBreakRisk)]
            elif query.risk_type == RiskType.REFILL_ABANDONMENT:
                filtered = [r for r in filtered if isinstance(r, RefillAbandonmentRisk)]
        
        if query.bundle_id:
            filtered = [r for r in filtered if (hasattr(r, 'bundle_id') and r.bundle_id == query.bundle_id)]
        
        if query.member_id:
            filtered = [r for r in filtered if (hasattr(r, 'member_id') and r.member_id == query.member_id)]
        
        if query.refill_id:
            filtered = [r for r in filtered if (hasattr(r, 'refill_id') and r.refill_id == query.refill_id)]
        
        if query.min_probability is not None:
            if isinstance(filtered[0], BundleBreakRisk):
                filtered = [r for r in filtered if r.break_probability >= query.min_probability]
            else:
                filtered = [r for r in filtered if r.abandonment_probability >= query.min_probability]
        
        if query.max_probability is not None:
            if isinstance(filtered[0], BundleBreakRisk):
                filtered = [r for r in filtered if r.break_probability <= query.max_probability]
            else:
                filtered = [r for r in filtered if r.abandonment_probability <= query.max_probability]
        
        if query.severity:
            filtered = [r for r in filtered if r.break_severity == query.severity or r.abandonment_severity == query.severity]
        
        if query.assessment_timestamp_from:
            filtered = [r for r in filtered if r.assessment_timestamp >= query.assessment_timestamp_from]
        
        if query.assessment_timestamp_to:
            filtered = [r for r in filtered if r.assessment_timestamp <= query.assessment_timestamp_to]
        
        return filtered
    
    def _sort_risk_assessments(self, risks: List[Union[BundleBreakRisk, RefillAbandonmentRisk]], sort_by: str, sort_order: str) -> List[Union[BundleBreakRisk, RefillAbandonmentRisk]]:
        """Sort risk assessments by specified field"""
        reverse = sort_order.lower() == "desc"
        
        if sort_by == "assessment_timestamp":
            return sorted(risks, key=lambda r: r.assessment_timestamp, reverse=reverse)
        elif sort_by == "break_probability":
            return sorted(risks, key=lambda r: r.break_probability if hasattr(r, 'break_probability') else r.abandonment_probability, reverse=reverse)
        elif sort_by == "abandonment_probability":
            return sorted(risks, key=lambda r: r.abandonment_probability if hasattr(r, 'abandonment_probability') else r.break_probability, reverse=reverse)
        elif sort_by == "confidence_score":
            return sorted(risks, key=lambda r: r.confidence_score, reverse=reverse)
        else:
            # Default sort by assessment timestamp
            return sorted(risks, key=lambda r: r.assessment_timestamp, reverse=reverse)
    
    def _generate_risk_summary(self, risks: List[Union[BundleBreakRisk, RefillAbandonmentRisk]]) -> RiskAssessmentSummary:
        """Generate summary statistics for risk assessments"""
        if not risks:
            return RiskAssessmentSummary(
                assessment_timestamp=datetime.now(timezone.utc),
                model_version=self.config.model_version,
                total_assessments=0,
                avg_break_probability=0.0,
                avg_abandonment_probability=0.0,
                high_risk_count=0,
                assessment_time_ms=0
            )
        
        # Separate risk types
        bundle_risks = [r for r in risks if isinstance(r, BundleBreakRisk)]
        abandonment_risks = [r for r in risks if isinstance(r, RefillAbandonmentRisk)]
        
        # Calculate aggregates
        total_assessments = len(risks)
        avg_break_prob = statistics.mean([r.break_probability for r in bundle_risks]) if bundle_risks else 0.0
        avg_abandon_prob = statistics.mean([r.abandonment_probability for r in abandonment_risks]) if abandonment_risks else 0.0
        
        high_risk_count = len([r for r in risks if r.break_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL] or 
                                           r.abandonment_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]])
        
        # Risk distribution
        risk_distribution = {
            "bundle_break": len(bundle_risks),
            "refill_abandonment": len(abandonment_risks)
        }
        
        severity_distribution = {}
        for risk in risks:
            severity = risk.break_severity if isinstance(risk, BundleBreakRisk) else risk.abandonment_severity
            severity_distribution[severity.value] = severity_distribution.get(severity.value, 0) + 1
        
        return RiskAssessmentSummary(
            assessment_timestamp=datetime.now(timezone.utc),
            model_version=self.config.model_version,
            total_assessments=total_assessments,
            risk_distribution=risk_distribution,
            severity_distribution=severity_distribution,
            avg_break_probability=avg_break_prob,
            avg_abandonment_probability=avg_abandon_prob,
            high_risk_count=high_risk_count,
            assessment_time_ms=sum(r.computation_time_ms for r in risks if hasattr(r, 'computation_time_ms'))
        )
