# Issue I21: Validate Against PHI Denylist

## Summary
Added PHI denylist enforcement during ingestion validation. Events containing prohibited PHI fields are rejected before canonicalization.

## Objectives
- Block ingestion of PHI fields (names, DOB, address, contact info, SSN, MRN)
- Provide clear validation errors for denylisted fields

## Architecture

### Validation Enhancements
**File:** `src/utils/validation.py`
- Added `phi_denylist_fields` set
- `_validate_phi_denylist` checks event payload for denylisted keys
- Validation fails if any denylisted field is present and non-empty

## Denylisted Fields
- Names: `first_name`, `last_name`, `full_name`, `member_name`, `patient_name`
- DOB: `dob`, `date_of_birth`, `birth_date`
- Contact: `email`, `phone`, `phone_number`
- Address: `address`, `street_address`, `city`, `state`, `zip`, `postal_code`
- Identifiers: `ssn`, `social_security_number`, `medical_record_number`, `mrn`

## Testing
Added ingestion test to ensure PHI fields are rejected.

**Tests:**
```
pytest tests/test_ingestion/test_processors.py
```

## Status
✅ Complete
