# Issue I8: Build Explainability Layer for Bundle Risks

## Objective
Create a reusable explainability layer that surfaces **top drivers with evidence** for bundle break, abandonment, shipment split, and fulfillment delay risks. The layer should provide clear narratives, supporting metrics, and recommendation rationales while remaining auditable and versioned.

## Scope
- Explain **why** a risk score was assigned.
- Surface **top drivers** with evidence and confidence.
- Provide **executive summary + detailed narrative**.
- Attach **recommendation rationales**.
- Support **query and pagination**.
- Provide optional **comparative** and **historical** context.

## Inputs
- **Risk assessments** (BundleBreakRisk, RefillAbandonmentRisk, shipment risks once available)
- **Bundle metrics** (age-in-stage, timing overlap, refill gap, bundle alignment)
- **Risk drivers + recommendations** from risk scoring engine
- Optional **history/trends** (prior risk assessments)

## Outputs
- **BundleRiskExplanation** object:
  - executive_summary
  - key_takeaways
  - primary/secondary driver explanations
  - evidence list per driver
  - recommendation explanations
  - optional comparative/historical/predictive context

## Data Model (Summary)
- **Evidence**: metric values, threshold comparisons, trend insights
- **RiskDriverExplanation**: impact level, narrative, evidence
- **RecommendationExplanation**: rationale + expected impact
- **BundleRiskExplanation**: full explainability payload
- **ExplanationQuery / ExplanationList**: retrieval APIs

## Explainability Engine Responsibilities
1. **Rank drivers** by impact + confidence.
2. **Generate evidence** per driver:
   - metric values
   - threshold deltas
   - trend markers (optional)
3. **Compose summaries**:
   - 1–2 sentence executive summary
   - 3–5 key takeaways
4. **Attach recommendation rationale**:
   - link recommendation → drivers
   - expected mitigation impact
5. **Compute confidence**:
   - driver confidence aggregate
   - evidence completeness

## Confidence Strategy
- **Driver confidence**: mean of top driver confidence
- **Evidence completeness**: ratio of expected evidence items present
- **Overall confidence**: weighted blend of driver confidence + evidence completeness

## Query & Retrieval
- Filter by risk type, bundle id, time range
- Pagination with limit/offset
- Optional inclusion of visualizations/historical context

## Versioning & Audit
- Include **explanation_version** and **model_version** in every explanation
- Log explainability generation in audit trail (future extension)

## Testing Strategy
- Validate driver ranking + evidence creation
- Verify summary generation
- Query filters + pagination
- Confidence and completeness calculation

## Integration Points
- **Risk Scoring Engine**: primary input
- **Metrics Engine**: evidence source
- **Audit Logger**: traceability

---

**Status**: In progress
**Dependencies**: Issues I5–I7
**Next Step**: Implement explainability engine and tests
