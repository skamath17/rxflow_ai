# Issue I20: Enforce Pseudonymization & ID Hygiene

## Summary
Implemented stricter **pseudonymization enforcement** for identifier fields during ingestion validation. Events with non-pseudonymous identifiers are rejected.

## Objectives
- Reject non-pseudonymous identifiers across ingestion inputs
- Enforce ID hygiene for `event_id`, `member_id`, `refill_id`, and optional `bundle_id`
- Validate `member_refills` identifiers on bundle events

## Architecture

### Validation Enhancements
**File:** `src/utils/validation.py`
- Added `_is_pseudonymous_id` helper
- Enforced pseudonymized format for identifiers
- Applied checks to bundle `member_refills` payloads

### Pseudonymization Rules
Identifiers must:
- Be at least 8 characters
- Match `[A-Za-z0-9_-]+`
- Not contain emails (`@`) or SSN patterns (`123-45-6789`)
- Not look like raw phone numbers

## Testing
Updated tests to validate rejection of non-pseudonymous IDs and ensure fixtures meet the stricter rules.

**Tests:**
```
pytest tests/test_ingestion/test_processors.py tests/test_models/test_events.py
```

## Status
✅ Complete
