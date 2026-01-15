# PharmIQ – Project Specification
**Risk Intelligence for Refill Bundling & Outreach Optimization**

---

## 1. Purpose
PharmIQ is an IP-driven, AI-enabled **risk intelligence layer** designed to augment CenterSync and related pharmacy workflows.  
Its goal is to **proactively detect and explain bundle breaks, shipment splits, and outreach waste** before they occur.

PharmIQ does **not** replace existing refill logic or execution systems.

---

## 2. Business Objectives
- Reduce multiple shipments per member
- Minimize redundant outreach (calls / SMS / email)
- Prevent inventory inefficiencies caused by fragmented refills
- Support executive goal of **$10–15M annual savings**
- Improve member experience and operational resilience

---

## 3. In-Scope Problems
PharmIQ addresses *risk and exception intelligence* related to:
- Refill timing mismatches
- Prior Authorization (PA) delays
- Out-of-stock (OOS) interruptions
- Shipment splits caused by asynchronous fulfillment
- Redundant outreach triggers

---

## 4. Out of Scope
- Replacing CenterSync refill rules
- Order creation or fulfillment execution
- Autonomous member communications
- Claims adjudication or pricing logic

---

## 5. High-Level Solution Overview
PharmIQ continuously analyzes refill lifecycle signals to:
1. Detect **bundle break risk**
2. Detect **shipment split & outreach waste risk**
3. Explain *why* the risk exists
4. Recommend **bundle-preserving actions** with human-in-loop controls

---

## 6. System Positioning
| Layer | Responsibility |
|-----|----------------|
| CenterSync | Refill eligibility, bundling rules, execution |
| PharmIQ | Risk detection, explainability, recommendations |
| HPIE / HPC | Order creation and outreach execution |

PharmIQ is **read-only + advisory**.

---

## 7. Key Capabilities
- Canonical refill & bundle event ingestion
- Refill snapshot aggregation
- Explainable risk scoring
- Bundle-aware recommendations
- Action and outcome tracking
- Executive savings visibility

---

## 8. Data Inputs (Logical)
- Refill lifecycle events
- PA status and duration
- Inventory availability flags
- Refill timing and overlap indicators
- Historical member refill behavior

> All identifiers must be pseudonymized.  
> No PHI is persisted.

---

## 9. Risk Types
- **Bundle Break Risk** – likelihood that a member’s refills will not ship together
- **Shipment Split Risk** – likelihood of multiple shipments
- **Outreach Waste Risk** – likelihood of redundant communications
- **Abandonment Risk** – likelihood refill is never completed

---

## 10. Explainability Principles
- Every risk score must include:
  - Top contributing drivers
  - Human-readable evidence
- No black-box predictions
- Versioned scoring and explainability logic

---

## 11. Recommendations (Advisory Only)
Examples:
- Delay refill to preserve bundle
- Advance refill to align shipment
- Suppress redundant outreach
- Escalate PA or inventory resolution

All recommendations require **human approval**.

---

## 12. Non-Functional Requirements
- Deterministic outputs
- Full audit trail (event → snapshot → risk → action)
- Production-grade reliability
- SRE-ready (monitoring, alerting)
- CI/CD enabled

---

## 13. Success Metrics
- Reduction in shipments per member
- Reduction in outreach volume
- % bundle breaks detected early
- Intervention success rate
- Estimated cost savings

---

## 14. Delivery Phases
**Phase 1:** Core ingestion, snapshot, risk detection  
**Phase 2:** Recommendations, dashboards, outcomes  
**Phase 3:** Optimization, scale, AI-assisted enhancements

---

## 15. Guiding Principles
- Complement, never compete with, CenterSync
- Explainability over accuracy
- Business outcomes over technical novelty
- IP-first, reusable architecture

---
