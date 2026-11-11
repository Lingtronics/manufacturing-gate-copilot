# Domain model

Every persistent entity has a stable ID. Evidence repository keys are `document ID@revision`. Other keys are domain IDs. SQLite `records(kind,id,body)` has a composite primary key. Pydantic validates fixture ingestion and domain reads.

| Entity | Meaning / links |
|---|---|
| Project | Synthetic programme, participants, gate ID |
| GateDefinition | Policy/document/version, rule labels, required requirement IDs |
| GateRequirement | Criteria, criticality, mandatory flag, document IDs |
| EvidenceDocument | Revision/text/type/location, requirement links and hash |
| EvidenceReference | Document/revision/paragraph, quotation and hash |
| QualityIssue | Severity, resolved flag, requirements and sources |
| EngineeringChange | Status and independent validation-complete flag |
| CorrectiveAction | Issue, owner, due date, blocking flag and status |
| AssessmentFinding | Rule/category/source record, requirements, verified references |
| GateAssessment | Version/policy/snapshot, readiness/coverage/counts, frozen sources |
| ReviewDecision | Actor, assessment version, acknowledgement/changes, note/time |
| PublicationApproval | Assessment/version/scene/actor/destination/time/status |
| MiroPublication | Approval, mode, board, status, result and optional real URL |
| KpiBaseline | Synthetic hours/reviews/rate/cycle/coverage/optional recurrence |
| ValueScenario | Versioned reductions, costs, adoption and review volume |
| AuditEvent | Actor, event, entity, correlation, time, safe details |

Distinct enums cover requirement criticality, evidence status, issue severity, action status, change status, readiness, review and publication. Unknown fields fail validation. VALIDATED changes require completed validation. Negative costs/hours/counts and percentages outside 0–1 are rejected. Incomplete blocking actions must reference unresolved HIGH/CRITICAL issues at fixture import.

`manifest.json` records exact counts and expected totals. Requirements, evidence revisions, issues, changes and actions have explicit expected classifications. DOC-004 A accepts a supplier part and B rejects it; both remain active. DOC-001/008 preserve missing-source metadata. REQ-003/006/011 are partial. Expected result: 9/15 requirements validated, four blockers, five insufficiency findings and four warnings.

The policy is `policy.md`, with requirement records and `gate.json`. These criteria are synthetic examples, not safety certification or manufacturing standards. The policy itself is included in the snapshot.

## Financial semantics

Decimal with ROUND_HALF_UP at display boundaries. Adoption multiplies realised hours. Hours = `(preparation × reduction + collection × reduction) × adoption × review volume`. Gross = hours × labour rate. Annual net = gross − operating cost. First-year net = annual net − implementation. ROI = first-year net / implementation × 100; zero implementation gives null. Payback = implementation / positive annual net; otherwise null. Zero implementation with positive net gives zero payback.

Cycle time/coverage/recurrence are baseline context, not assumed improvements. No defect avoidance, revenue uplift or launch acceleration is inferred. Baseline/scenario inputs persist; calculation output includes assumption version and inputs.
