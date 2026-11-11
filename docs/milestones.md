# Milestone execution record

Date: 2026-10-24. Work proceeded in the current empty directory. No source was overwritten and the neighbouring Data Room Cited repository was inspected read-only. No copied source was used because no explicit reuse licence was found.

This log groups related verification runs where features shared a milestone. It does not imply an unrecorded test run for every scaffold directory.

| Specification milestone | Completed work | Actual verification |
|---|---|---|
| 1. Scaffold/environment | Backend/frontend layout, config template and original SPEC | Python compileall and Ruff passed |
| 2. Domain/fixtures | 17 entity models, enums, synthetic manifest and source revisions | Initial unit suite: 2 passed after correcting fixture-root path |
| 3. Persistence/evidence | SQLite ingestion, exact/lexical lookup and verified quotes | Initial 2 tests and later ingestion/restart/citation tests in final suite |
| 4. Deterministic engine | All six rules, coverage and precedence | Fixture result validated; expanded isolated rule/golden cases all pass |
| 5. API | Required routes, session auth, permission checks and versioning | First API-integrated suite: 9 passed |
| 6. Board scene/preview | Seven sections, stable grid/keys, source IDs and HTML preview | Geometry/stability/escaping tests; preview inspected in Chromium |
| 7. Mock adapter | Durable mappings/reconciliation and partial failure | API tests verify repeat publication and unrelated preservation |
| 8. Review/approval | Distinct identities/permissions, hashes, supersession and explicit publish | Permission and changed review/source/scene tests pass |
| 9. Live REST adapter | Official reference review, distinct resources, bounded retries and ambiguity journal | Transport mocks test supported routes, 429, create timeout/5xx/malformed ambiguity; real integration remains unvalidated |
| 10. Finance | Decimal calculation, three scenarios and persisted assumptions | Known base computation, half-up rounding, negatives and zero cases pass |
| 11. React frontend | Five responsive typed views and complete controls | TypeScript/Vite builds pass; real-browser workflow/mobile checks pass |
| 12. Readout/sprint | Ten-section report/export and fictional charter | Browser download tested; standalone report/preview generated |
| 13. Hardening/evaluation | JSON/Markdown ingestion, offline API docs, redaction, persisted recovery lock | Final combined suite: 47 backend tests, 2 Chromium tests; lint/type/format/build pass |

## Failures found and resolved

- Early file-write commands used a missing helper directory and an incorrect working directory; no existing user data was affected. The scaffolding commands were corrected.
- An off-by-one filesystem parent count initially missed fixtures; corrected and retested.
- Sandboxed Windows loopback sockets blocked TestClient startup. Tests were rerun with allowed local socket access and completed.
- Windows temporary-directory access required a project-local fresh test directory; final check script creates one explicitly.
- Browser notification exact-text assertion included the dismiss icon; assertion corrected after inspecting the actual rendered result.
- Browser repetition exposed random-ID ordering in publication history. API responses now order publications by timestamp, and the UI displays results bound to the current approval. Verified by the full browser flow.
- An intermediate editor helper used Windows-default encoding and truncated a newly created component; restored from the authored source, rebuilt and rerun before final validation.
- Python typing issues were fixed; final mypy checks cover 27 app source files.

Final raw evidence is [verification.log](verification.log). Optional Miro, actual Ollama inference and Docker runtime are explicitly unvalidated. No customer benefit or real sprint result is claimed.


## Integration upgrade — 2026-11-11

Actual local Ollama inference and its browser path are now validated. Miro read-back verification, bounded pagination and an explicit approval-bound live validator are implemented; actual Miro publication still needs credentials and an authorised board. See the [live integration report](live-integration-validation.md).
