# PharmIQ - Risk Intelligence for Refill Bundling & Outreach Optimization

## Project Structure
```
pharmiq/
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── events.py          # Canonical event schemas
│   │   ├── snapshots.py       # Refill snapshot models
│   │   └── risks.py           # Risk scoring models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── api.py            # Event ingestion endpoints
│   │   └── processors.py     # Event processing logic
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── bundle_risk.py    # Bundle break risk scoring
│   │   └── explainability.py # Risk explainability
│   └── utils/
│       ├── __init__.py
│       ├── validation.py     # Data validation utilities
│       └── audit.py          # Audit logging utilities
├── tests/
│   ├── __init__.py
│   ├── test_models/
│   │   ├── test_events.py
│   │   ├── test_snapshots.py
│   │   └── test_risks.py
│   ├── test_ingestion/
│   │   ├── test_api.py
│   │   └── test_processors.py
│   └── conftest.py           # Pytest configuration
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Phase 1 Focus
- **Epic E1**: PharmIQ Core Platform
- **Issue I1**: Define canonical refill & bundle event schema
- **Tasks**: Design → Implement → Test (with pytest)

## Key Principles
- All identifiers must be pseudonymized
- No PHI persisted
- Full audit trail (event → snapshot → risk → action)
- Deterministic outputs
- Explainable risk scoring
