# Issue I14: Build Ops Work Queue for Bundle Risks

## Summary
Implemented an **ops work queue** to list members/refills at risk of bundle break or shipment split, enabling operational follow‑up on high‑risk items.

## Objectives
- Surface bundle risk items in a queue
- Track queue status and assignments
- Provide quick filtering by status or bundle

## Architecture

### Core Components
1. **Queue Models (`src/models/work_queue.py`)**
   - `BundleRiskQueueItem`
   - `QueuePriority`
   - `QueueItemStatus`

2. **Ops Queue Engine (`src/ops_queue/ops_work_queue_engine.py`)**
   - Create queue items from risk assessments
   - Update status and assignment
   - List by status or bundle

3. **Exports**
   - Models exported in `src/models/__init__.py`
   - Engine exposed via `src/ops_queue/__init__.py`

## Data Flow
1. Risk engine emits `BundleBreakRisk` or `RefillAbandonmentRisk`
2. Ops queue engine creates `BundleRiskQueueItem`
3. Ops team updates status and assignment

## Status States
- **Open**: newly created
- **In Progress**: actively worked
- **Resolved**: addressed
- **Dismissed**: deemed not actionable

## Testing
Tests cover:
- Queue creation from risk
- Status updates
- Listing by status

**Tests:**
```
pytest tests/test_ops_queue
```

## Status
✅ Complete
