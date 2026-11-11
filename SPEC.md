# Manufacturing Gate Copilot — Codex Master Specification

Version: 1.0  
Status: Approved implementation target  
Repository: manufacturing-gate-copilot  
Date: 2026-10-24

## A. Engineering mission

Build a standalone, working AI-powered Manufacturing Quality & Stage-Gate Review Copilot.

This is a portfolio-quality demonstration for a manufacturing-focused forward deployed consulting role. It must combine credible manufacturing process modelling, evidence-grounded AI, deterministic risk assessment, Miro collaboration and transparent business-value analysis.

Implement the project in the current working directory.

The application must run locally with synthetic data without requiring any third-party API credentials.

Live Miro and LLM integrations must be opt-in.

### Non-negotiable instructions

1. Create a new, independent application. Do not modify the existing Data Room Cited repository.
2. Do not make Data Room Cited a runtime dependency.
3. If its source code is available locally, inspect it read-only and selectively reuse proven patterns or code where legally and technically appropriate. Respect licensing and attribution.
4. Implement the specified features, not just architecture documentation.
5. Keep the implementation small, modular, typed, testable and reproducible.
6. Do not invent manufacturing facts or real-world business outcomes.
7. Distinguish source evidence, AI interpretation, deterministic findings and human decisions.
8. Keep real Miro operations disabled unless explicitly authorised.
9. Never expose API credentials to the browser, model prompts or logs.
10. Do not push code or deploy externally without approval.
11. Run tests and report actual results after each milestone.
12. If a required integration is unavailable, complete and test its local mock equivalent.
13. Continue through implementation milestones without requesting routine confirmations, but stop before destructive or externally consequential operations requiring authorisation.

## B. Product scenario

The fictional customer is Northstar Manufacturing.

It manufactures automated material-handling equipment and is preparing for its Gate 3 production-readiness review.

The gate determines whether the product has sufficient engineering, quality and operational evidence for a human-led progression decision.

Current challenges:

- Quality records are scattered across different systems and documents.
- Requirements lack consistent evidence traceability.
- Engineering changes may be approved but not validated.
- Defect closure and corrective actions are difficult to review.
- Gate-review preparation is manual.
- Leaders lack a consistent view of readiness and operational risks.

The Copilot should consolidate the evidence, identify unresolved issues, recommend review actions, build a collaborative Miro board and calculate a hypothetical business-value case.

This is decision support only.

It must never autonomously authorise production launch.

## C. Functional requirements

### FR-01: Synthetic manufacturing programme

Provide one preloaded programme:

- Name: Northstar Automated Sortation Line.
- Review: Gate 3 — Pilot Production Readiness.
- Data: Entirely synthetic.
- Participants: Engineering, Quality, Manufacturing Operations and Programme Management.

Create:

- 15 gate requirements.
- 10 supporting evidence documents.
- 8 quality issues.
- 5 engineering changes.
- 8 corrective actions.
- 1 KPI baseline dataset.
- 1 gate policy document.

All records must be internally consistent, linked by stable identifiers and documented in a fixture manifest.

Include a mixture of complete, incomplete, contradictory and unresolved records.

Each fixture must have an explicit expected classification, where applicable.

### FR-02: Domain entities

Implement typed Pydantic models and persistent representations for:

- Project
- GateDefinition
- GateRequirement
- EvidenceDocument
- EvidenceReference
- QualityIssue
- EngineeringChange
- CorrectiveAction
- AssessmentFinding
- GateAssessment
- ReviewDecision
- PublicationApproval
- MiroPublication
- KpiBaseline
- ValueScenario
- AuditEvent

Each record must have a stable internal ID.

Use explicit enumerations for:

- Requirement criticality.
- Evidence status.
- Issue severity.
- Action status.
- Engineering change status.
- Gate readiness.
- Review status.
- Publication status.

Do not collapse these into a single generic status field.

### FR-03: Evidence processing

Implement a local evidence ingestion and indexing pipeline.

Inputs:

- JSON manufacturing records.
- Markdown evidence documents.

Store source metadata and stable content references.

Each evidence item should preserve:

- Document ID.
- Revision.
- Source type.
- Source text.
- Relevant requirement IDs.
- Location or paragraph reference.
- Document content hash.

Requirements:

- Exact-ID retrieval must always work.
- Basic lexical search must work without an LLM.
- Semantic retrieval is optional, behind an interface.
- Source quotations must be validated against stored source content.
- Conflicting source revisions must be surfaced.
- No finding may cite an unknown document.
- Retrieval and citation validation must be deterministic and testable.

Avoid building a heavyweight vector database for the MVP.

### FR-04: Gate assessment engine

Implement a deterministic rules engine.

Required rule identifiers:

GATE-001 — Critical requirement evidence missing.

GATE-002 — High-severity quality blocker unresolved.

GATE-003 — Engineering change validation incomplete.

GATE-004 — Conflicting supporting evidence.

GATE-005 — Non-blocking corrective action outstanding.

GATE-006 — Mandatory source evidence unavailable.

Assessment output:

- assessment_id
- project_id
- policy_version
- source_snapshot_hash
- assessment_version
- overall_readiness
- requirement_coverage
- blocker_count
- warning_count
- findings
- evidence_references
- generated_at

Use the following readiness precedence:

1. If a known critical blocker exists, NOT_READY.
2. Else, if mandatory evidence is insufficient or contradictory in a way that prevents assessment, INSUFFICIENT_EVIDENCE.
3. Else, if reviewable non-blocking work remains, CONDITIONAL_REVIEW.
4. Otherwise, READY_FOR_REVIEW.

The criteria and criticality of each gate requirement must be defined by the synthetic gate policy, not invented by an LLM.

A status of READY_FOR_REVIEW means the evidence is ready for human review, not that production has been authorised.

Calculate requirement coverage explicitly.

For example:

Coverage = requirements with validated supporting evidence / total required requirements × 100.

Document how partial and contradictory evidence are counted.

### FR-05: AI explanation service

Define an interface:

AssessmentExplainer.generate(assessment, supporting_evidence)

Implement two providers:

1. TemplateExplainer — deterministic local implementation.
2. LLMExplainer — optional configured model provider.

The LLM can:

- Summarise evidence-backed findings.
- Explain relationships between requirements and defects.
- Suggest review questions.
- Draft an executive narrative.

The LLM cannot:

- Change deterministic gate status.
- Invent source references.
- Mark corrective actions complete.
- Approve engineering changes.
- Authorise publication.
- Make unsupported financial claims.

Validate structured model outputs using Pydantic.

If the model fails, return the deterministic explanation.

Use bounded model timeouts.

Include prompt-injection test fixtures.

### FR-06: Miro board scene model

Create a provider-independent scene model:

- BoardScene
- BoardSection
- BoardItem
- BoardConnector
- BoardStyle
- PublicationOperation

Generate a deterministic scene from a GateAssessment.

The scene must include:

1. Executive summary.
2. Requirements and evidence.
3. Quality risk register.
4. Engineering changes.
5. Corrective actions.
6. Human decision log.
7. Business-value summary.

Implement a pure function:

build_board_scene(assessment, project, value_case) -> BoardScene

Include stable keys for all generated items.

Separate domain objects from visual layout coordinates.

Use a predictable grid layout.

Requirements:

- No overlapping sections.
- Readable content lengths.
- Consistent labels and severity states.
- Stable item order.
- Source evidence references.
- No unapproved decisions.
- HTML/text content sanitisation.

Provide an HTML or SVG preview generated locally from the scene model.

The preview must not call Miro.

### FR-07: Miro REST integration

Implement a MiroAdapter interface with:

- create_board
- get_board
- create_items
- update_item
- list_managed_items
- reconcile_publication

Provide:

- MockMiroAdapter.
- RestMiroAdapter.

The live adapter must use the documented Miro REST API v2.

Use:

https://api.miro.com/v2

Review official request/response schemas before implementation:

https://developers.miro.com/reference/overview
https://developers.miro.com/reference/create-board-1
https://developers.miro.com/reference/create-items
https://developers.miro.com/reference/rate-limiting

Do not assume identical schemas for every board-item type.

Where bulk creation is suitable, use documented batches of at most 20 items. Verify supported item types and payloads.

Check the current documentation for frames, shapes, sticky notes, text items, connectors and update operations.

Do not invent unsupported endpoints.

Use least-privilege scopes.

For live REST API access, use an authorised OAuth token and documented OAuth procedures. A manually supplied valid token may be supported for local development, but do not treat an arbitrary API key as equivalent to OAuth authorisation.

Save remote board and item IDs.

Implement local managed-item mappings.

Repeated publication must:

- Reconcile known item IDs.
- Update changed managed items.
- Preserve unchanged managed items.
- Add genuinely new items.
- Leave unrelated board items untouched.
- Report ambiguous or partial failures.
- Never automatically clear or recreate the entire board.

Use bounded retries and rate-limit handling.

Do not blindly replay ambiguous create requests.

### FR-08: Review and publication approval

Model review and publication as distinct permissions.

Assessment lifecycle:

DRAFT
→ ASSESSED
→ REVIEWED

Publication lifecycle:

PREVIEW
→ APPROVAL_PENDING
→ APPROVED
→ PUBLISHING
→ PUBLISHED

Support FAILED and SUPERSEDED states where appropriate.

Implement local demo roles:

- Analyst.
- Reviewer.
- Publisher.

Keep authentication and authorisation separate.

Use a local development identity provider or demo session mechanism that is explicitly labelled non-production.

Do not trust a client-submitted role header in deployed mode.

Publication approval must bind to:

- Assessment ID and version.
- Scene content hash.
- Actor.
- Intended destination board.
- Timestamp.

Any material change to the assessment or scene must invalidate prior approval.

Make the final publication operation a separate explicit step.

Audit all approval and publication transitions.

### FR-09: Business-value calculation

Implement pure deterministic functions.

KPI baseline inputs:

- Evidence collection hours per gate.
- Gate review preparation hours.
- Number of annual reviews.
- Labour cost per hour.
- Current gate cycle time.
- Current evidence coverage.
- Defect recurrence where valid data exists.

Scenario assumptions:

- Expected preparation-time reduction.
- Expected evidence collection reduction.
- Implementation cost.
- Annual operating cost.
- Adoption rate.
- Annual review volume.

Financial outputs:

- Annual hours saved.
- Annual gross benefit.
- Annual net benefit.
- First-year net benefit.
- First-year ROI.
- Simple payback period, if calculable.

Use Decimal for monetary calculations.

Explicitly define whether adoption rate affects realised hours saved.

Separate conservative, base and optimistic scenarios.

Never assume avoided defect cost, revenue uplift or launch acceleration without supporting scenario inputs.

Reject negative costs and impossible percentages.

Handle zero-benefit and zero-cost conditions correctly.

Persist calculation inputs and assumption versions.

Clearly label every result as synthetic or modelled.

### FR-10: Application API

Implement versioned endpoints under `/api/v1`.

Minimum routes:

GET /health

GET /api/v1/projects

GET /api/v1/projects/{project_id}

GET /api/v1/projects/{project_id}/requirements

GET /api/v1/projects/{project_id}/evidence

POST /api/v1/projects/{project_id}/assessments

GET /api/v1/assessments/{assessment_id}

GET /api/v1/assessments/{assessment_id}/findings

GET /api/v1/assessments/{assessment_id}/board-preview

POST /api/v1/assessments/{assessment_id}/review

POST /api/v1/assessments/{assessment_id}/publication-approvals

POST /api/v1/assessments/{assessment_id}/publish

GET /api/v1/projects/{project_id}/value-case

GET /api/v1/projects/{project_id}/executive-report

Use repository-consistent request and response contracts.

Generate OpenAPI documentation.

Use explicit HTTP errors.

Sensitive and state-changing endpoints must enforce appropriate authorisation.

### FR-11: Frontend

Implement a React/TypeScript application with five primary views.

**Dashboard**

- Project name.
- Gate status.
- Requirement coverage.
- Open quality blockers.
- Pending engineering changes.
- Review and publication status.

**Evidence Explorer**

- Requirements.
- Source documents.
- Verified citations.
- Missing or conflicting evidence.

**Gate Assessment**

- Findings.
- Rule identifiers.
- Blocker explanation.
- Review status.
- Human reviewer actions.

**Miro Workspace**

- Local visual preview.
- Miro publication status.
- Approval controls.
- Published board link when available.

**Executive Value Case**

- KPI baseline.
- Scenario assumptions.
- ROI comparison.
- Business recommendations.
- Executive report.

Use a clean, manufacturing-appropriate visual language.

Prioritise readability, traceability and concise executive summaries.

Never simulate a live Miro publication as successful when only a local preview exists.

### FR-12: Executive report

Produce a downloadable or copyable Markdown executive report.

Sections:

1. Executive summary.
2. Manufacturing operating problem.
3. Gate readiness.
4. Quality and validation risks.
5. Evidence completeness.
6. Recommended corrective actions.
7. AI-enabled future workflow.
8. Financial scenarios and assumptions.
9. Risks and limitations.
10. Validation Sprint outcomes and next-step proposal.

Do not invent customer endorsement or achieved savings.

### FR-13: Validation Sprint package

Create a fictional, clearly labelled consulting Validation Sprint charter.

Include:

- Customer business objective.
- Executive sponsor persona.
- Opportunity hypothesis.
- Value baseline.
- Scope and exclusions.
- Data access assumptions.
- Two-week hypothetical sprint plan.
- Exit criteria.
- Success metrics.
- Risks.
- Proposed post-sprint implementation scope.

The software development project itself does not need to last two weeks. The charter represents the fictional customer engagement.

### FR-14: Observability and security

Include:

- Structured logs.
- Correlation IDs.
- Assessment versioning.
- Source snapshot hashes.
- Approval audit trail.
- Miro request status.
- Redacted exception reporting.
- Timeouts.
- Bounded retries.
- Controlled outbound operations.
- Prompt-injection resistance.
- Source/content sanitisation.
- Permission checks.

Use explicit capability boundaries for the LLM.

Never pass live API secrets to LLM prompts.

Only synthetic data may be published to Miro in this MVP.

## D. Repository structure

Create:

manufacturing-gate-copilot/
- backend/
  - app/
    - api/
    - core/
    - domain/
    - services/
      - evidence/
      - assessment/
      - ai/
      - miro/
      - value/
    - persistence/
    - schemas/
    - main.py
  - tests/
    - unit/
    - integration/
    - evaluation/
  - pyproject.toml
- frontend/
  - src/
    - api/
    - components/
    - pages/
    - types/
  - package.json
- fixtures/
  - northstar/
    - requirements/
    - evidence/
    - quality/
    - changes/
    - actions/
    - kpis/
    - manifest.json
- docs/
  - architecture.md
  - domain-model.md
  - security-model.md
  - miro-integration.md
  - validation-sprint.md
  - executive-readout.md
  - demo-script.md
- scripts/
- .env.example
- .gitignore
- docker-compose.yml
- README.md
- SPEC.md

Adapt structure where conventional packaging requires it.

Keep imports, build contexts and volume paths consistent.

## E. Test specification

### Unit tests

- Domain validation.
- Evidence references.
- Gate-rule precedence.
- Critical blocker detection.
- Contradictory evidence.
- Revision handling.
- Coverage calculation.
- Monetary rounding.
- Scenario computation.
- Approval state transitions.
- Scene layout generation.

### Integration tests

- Fixture loading.
- Assessment endpoint.
- Retrieval-to-finding traceability.
- Mock Miro publication.
- Repeated publication.
- Partial Miro failures.
- Rate-limit handling.
- Approval invalidation.
- Unsupported Miro operations.
- No credentials mode.

### Evaluation dataset

Provide golden cases covering:

- Complete requirement.
- Missing critical evidence.
- Unresolved major defect.
- Incomplete engineering validation.
- Conflicting revisions.
- Unsupported model explanation.
- Prompt-injection content.
- Non-blocking overdue action.

Treat all findings as synthetic.

Deterministic safety-critical rules must pass every corresponding golden test.

### End-to-end tests

From a clean installation:

1. Start application.
2. Load sample project.
3. Run assessment.
4. Review findings and evidence.
5. Preview board.
6. Approve publication as authorised demo user.
7. Publish through mock adapter.
8. Inspect item mappings.
9. Republish unchanged version.
10. Confirm no duplicates.
11. Generate ROI scenarios.
12. Generate executive report.

The full flow must work without external credentials.

Live Miro validation must be documented separately.

## F. Definition of Done

The implementation qualifies as an MVP only when:

- A clean installation works.
- Synthetic fixtures load reproducibly.
- All required domain models are validated.
- Gate readiness is deterministic.
- Evidence links are verifiable.
- Unsupported conclusions are rejected or qualified.
- Local board preview works.
- Mock Miro publication works.
- Publication approval is version-bound.
- Repeated publication is idempotent.
- Unrelated board items are preserved.
- ROI outputs reproduce known test calculations.
- Executive report is generated.
- Frontend demonstrates the core workflow.
- No secrets are included in the repository.
- Tests pass with actual execution records.
- Documentation accurately describes implemented and optional features.

Optional real Miro publication is not required for offline MVP completion, but is required before claiming live Miro integration has been demonstrated.

## G. Development workflow

Implement in this order:

1. Repository scaffold and environment configuration.
2. Domain models and synthetic fixtures.
3. Persistence, ingestion and evidence lookup.
4. Deterministic gate assessment.
5. API endpoints.
6. Board scene model and local preview.
7. Mock Miro adapter.
8. Review, approval and publication state machine.
9. Live Miro REST adapter.
10. Financial modelling.
11. React frontend.
12. Executive report and Validation Sprint package.
13. End-to-end evaluation and hardening.

After each step:

- Run relevant tests.
- Fix failures.
- Run linting and type checks.
- Update documentation.
- Record completed and incomplete items.

Avoid adding a major framework unless an existing requirement justifies it.

## H. Final delivery format

Provide:

- Implemented functionality.
- Architecture decisions.
- Folder/file inventory.
- Exact setup commands.
- Test commands.
- Test results.
- Mock and live Miro statuses.
- Known limitations.
- Remaining configuration.
- Demo walkthrough.
- Recommended v1.1 improvements.

Report each major capability as IMPLEMENTED, TESTED, PARTIAL, BLOCKED or NOT STARTED.

Do not claim a test ran unless it actually ran.

## I. Start execution now

Begin by confirming the working directory and inspecting its contents.

If the directory is empty, create the project.

If it contains existing code, do not overwrite it without inspection.

Generate the initial project scaffold and implement Phase 1.

Proceed sequentially through the phases, running the tests associated with each milestone.

The goal is a functioning demonstration, not a collection of design documents.