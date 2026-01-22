# Issue I12: Track Bundle-Preserving Actions

## Summary
Implemented an **action tracking layer** to capture lifecycle status and outcomes for bundle-preserving interventions derived from recommendations. This provides traceability from recommendation → execution → outcome.

## Objectives
- Track lifecycle status for recommended actions
- Associate actions to recommendation and bundle/member context
- Capture outcomes and notes for operational follow‑through
- Provide query utilities for downstream reporting

## Architecture

### Core Components
1. **Action Models (`src/models/actions.py`)**
   - `ActionStatus`: proposed → approved → in_progress → completed/cancelled
   - `ActionOutcome`: success/partial/failed/unknown
   - `TrackedAction`: action metadata and timestamps

2. **Action Tracking Engine (`src/actions/action_tracking_engine.py`)**
   - Creates tracked actions from `BundleRecommendation`
   - Updates status/outcome with notes
   - Retrieves actions by recommendation or status

3. **Exports**
   - Models exported in `src/models/__init__.py`
   - Engine exposed via `src/actions/__init__.py`

## Data Flow
1. Recommendation engine emits `BundleRecommendation`
2. Action tracking engine creates `TrackedAction`
3. Operations update status/outcome as work progresses
4. Reporting/analytics query by recommendation or status

## Lifecycle States
- **Proposed**: action created from recommendation
- **Approved**: approved for execution
- **In Progress**: active execution
- **Completed**: finished execution (requires outcome)
- **Cancelled**: dropped or superseded

## Testing
Tests cover:
- Action creation from recommendation
- Status and outcome updates
- Query by recommendation

**Tests:**
```
pytest tests/test_actions
```

## Status
✅ Complete
