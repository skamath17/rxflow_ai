# Issue I10: Build Bundle-Aware Recommendation Engine

## Summary
Implemented a **standalone recommendation engine** that converts risk-driven recommendations into bundle-aware actionable plans (delay/advance/suppress/outreach/monitor), with ranking and deduplication.

## Objectives
- Provide a dedicated recommendation pipeline
- Normalize recommendations into consistent action types
- Rank by priority and confidence
- Deduplicate overlapping actions

## Architecture

### Core Components
1. **Recommendation Models (`src/models/recommendation.py`)**
   - `RecommendationActionType`
   - `RecommendationPriority`
   - `RecommendationContext`
   - `BundleRecommendation`

2. **Recommendation Engine (`src/recommendation/recommendation_engine.py`)**
   - Converts `RiskRecommendation` into `BundleRecommendation`
   - Infers action type based on category/title
   - Ranks by priority then confidence
   - Deduplicates by action_type + title

3. **Exports**
   - Models exported in `src/models/__init__.py`
   - Engine exposed via `src/recommendation/__init__.py`

## Data Flow
1. Risk engine generates `RiskRecommendation`
2. Recommendation engine normalizes to `BundleRecommendation`
3. Ranking + dedupe produces final action list

## Action Types
- **Delay**: defer action to improve bundle alignment
- **Advance**: accelerate timing to preserve bundle
- **Suppress**: avoid redundant outreach
- **Outreach**: proactive member engagement
- **Monitor**: watchlist or passive actions

## Ranking & Deduping
- Priority order: urgent → high → medium → low
- Tie‑breakers by confidence
- Deduplicate by `(action_type, title)`

## Testing
Tests cover:
- Ranking order
- Dedupe behavior
- Action type inference

**Tests:**
```
pytest tests/test_recommendation
```

## Status
✅ Complete
