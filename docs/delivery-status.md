# Delivery status — updated 2026-11-11

The credential-free native MVP is implemented and tested. No code was pushed or externally deployed. No real Miro request was made. Local Ollama inference and its browser UI path were validated on 2026-11-11.

## Capability status

| Capability | Status | Evidence / practical limit |
|---|---|---|
| Independent scaffold and setup | TESTED | Fresh project directory; isolated Python 3.12 environment and pinned npm install/build |
| FR-01 synthetic programme | TESTED | Exact counts and classifications checked against manifest |
| FR-02 Pydantic domain/persistence | TESTED | All 17 entities, distinct enums, invalid-input and SQLite restart tests |
| FR-03 evidence processing | TESTED | JSON/Markdown ingestion, IDs, lexical search, revision conflicts and quote/hash/location checks |
| FR-04 deterministic gate engine | TESTED | All six rules and every readiness precedence tested |
| FR-05 template explanation | TESTED | Default credential-free provider |
| FR-05 optional LLM | TESTED | Actual llama3.2:1b baseline/injection inference and real-browser UI check pass; validated finding plans, visible fallback and caching implemented |
| FR-06 scene and local preview | TESTED | Seven sections, stable keys/order, bounds/non-overlap, escaping; browser iframe inspected |
| FR-07 mock publication | TESTED | 56 managed items, unchanged republish, changed item, unrelated preservation, partial/ambiguous failure handling |
| FR-07 live REST adapter | PARTIAL | Read-back/pagination/drift verification and explicit live validator implemented; actual publication awaits authorised board and OAuth token |
| FR-08 review/publication permissions | TESTED | Analyst/Reviewer/Publisher separation, stale approvals, changed scene/source/review, persisted publication lock |
| FR-09 financial modelling | TESTED | Decimal known calculations, invalid/zero inputs, three persisted scenario versions |
| FR-10 API and OpenAPI | TESTED | Required v1 endpoints, validated principal contracts, explicit errors and offline generated docs |
| FR-11 five-view frontend | TESTED | Full Chromium workflow and mobile navigation; TypeScript build and screenshots |
| FR-12 executive report | TESTED | API download/browser export; generated ten-section Markdown artifact |
| FR-13 fictional sprint package | IMPLEMENTED | Charter, personas, baseline, plan, exit criteria, metrics, risks and proposed next scope; no real customer sprint |
| FR-14 local security/observability | TESTED | Correlation, role/host/origin checks, redacted errors, audit, source snapshots and adversarial tests |
| Production authentication/deployment | NOT STARTED | Deliberately outside local MVP; production mode fails closed |
| Docker packaging | PARTIAL | Dockerfile/compose supplied; Docker executable unavailable, runtime not tested |

## Original MVP verification (2026-10-24)

Command: `./scripts/check.ps1`. Full captured output: [verification.log](verification.log).

- Python 3.12 isolated environment, pytest 8.3.4: **47 passed in 1.38 s**.
- One upstream Starlette/AnyIO deprecation warning; no failed/skipped tests.
- Ruff: **all checks passed**.
- Mypy: **no issues in 27 source files**.
- Prettier: **all matched files pass**.
- TypeScript + Vite production build: **passed**. Main bundle 229.10 kB, gzip 70.26 kB.
- Playwright Chromium: **2 passed in 7.5 s**. Full offline workflow and responsive source search.
- Six screenshots saved in `docs/screenshots`: dashboard, evidence, assessment, workspace, value case and mobile.

Browser tests started a fresh local database, ran an assessment, inspected verified evidence/conflicts, recorded human review, requested/approved publication as Publisher, published through mock, confirmed unchanged republish/no duplicates, inspected mappings, viewed ROI and downloaded the report. API tests additionally verify unrelated-item preservation, changed-item update, partial recovery, approval invalidation and persistent recovery locks.

## Demonstration baseline

NOT_READY; coverage 60.00%; 4 blockers; 5 insufficiency findings; 4 warnings. Base financial model: 238.08 hours/year, GBP 15,475.20 gross, GBP 13,075.20 recurring annual net, GBP 1,075.20 first-year net, 8.96% first-year ROI and 0.92-year simple payback. These are synthetic/modelled outputs, not achieved outcomes.

## Configuration and limitations

No configuration or credentials are needed for the default native demo. Start via README or `scripts/start.ps1`. Local SQLite persists work; memory-only demo sessions reset on server restart. Use a different DATABASE_PATH for a fresh trial without deleting data.

Live Miro needs separate human authorisation, an existing board, a valid OAuth token and both opt-in settings; see the Miro runbook. Ollama and llama3.2:1b are now installed and validated; opt in with scripts/start.ps1 -Ollama. Docker was unavailable. No integration is represented as live merely because a local mock operation succeeded.

Single-process local service, synthetic records only, no production SSO, revision-retirement UI, bulk REST execution, autonomous launch approval or achieved business-value claim. Ambiguous writes and crash locks need verified administrator recovery; the application refuses blind create replay. Domain SQL migrations and multi-worker operation are not implemented.

Recommended v1.1: SSO, controlled data/revision stewardship and adapters, transactional workflow/migrations, optimistic concurrency, live OAuth/drift validation, guided recovery, accessibility contrast audit, and measured customer baseline/adoption validation.

Setup, folder inventory and full walkthrough are in [README](../README.md). Architecture decisions are in [architecture](architecture.md). The original target is preserved in [SPEC](../SPEC.md).


## Integration upgrade verification (2026-11-11)

**61 backend tests pass**, **2 offline Chromium tests pass**, and **1 actual Ollama Chromium test passes**. Ruff, mypy (29 app files), frontend formatting and production build pass. The local-model baseline and injection calls both returned model_used with unchanged NOT_READY readiness and 13 grounded findings. Miro remains BLOCKED at live preflight because no board/token was supplied. Docker remains unvalidated. Full commands, logs and requirements: [live integration report](live-integration-validation.md).
