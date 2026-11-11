# Security and authority

This is a loopback-only synthetic demonstration. `APP_MODE` other than `demo` fails startup. Do not expose it publicly.

## Identity vs permission

`POST /api/v1/demo-sessions` selects a labelled demo identity. The server generates an opaque random token, stores its role server-side, and sets an HttpOnly SameSite=Strict cookie. Memory-only sessions expire after eight hours. Role headers cannot confer authority. Anyone with local access may intentionally select a demo role; this is explicitly non-production.

| Capability | Analyst | Reviewer | Publisher |
|---|---:|---:|---:|
| Read programme/evidence/findings/reports | Yes | Yes | Yes |
| Create assessment version | Yes | No | No |
| Record human review | No | Yes | No |
| Request publication approval | Yes | No | Yes |
| Approve and execute publication | No | No | Yes |
| Inspect operation journal | No | No | Yes |

No production-launch approval API exists. Review acknowledges the evidence and unresolved risks; publication shares an exact scene. Neither clears issues or validates engineering changes.

## Browser boundary

Trusted-host and loopback checks protect demo sessions. Unsafe requests with unexpected Origin fail. SameSite=Strict cookies and same-origin API calls avoid cross-origin role submission. Loopback HTTP cookies omit Secure intentionally; production would require HTTPS/SSO and deployed CSRF controls. No wildcard CORS. Responses set CSP, nosniff, no-store and referrer policy. Local docs/preview have no external scripts. React escapes source text, preview HTML escapes source-derived content, Miro content is escaped and length-bounded, and preview iframe permissions are empty.

Compose permits private container clients because Docker changes client addresses; its host port remains bound to 127.0.0.1. Never enable `DEMO_ALLOW_PRIVATE_CLIENTS` for a public deployment.

## Model boundary

Default explanation is a deterministic template. Optional inference is fixed to local Ollama with a configurable 30-second timeout (bounded to 1–60 seconds) and no tools. Only grounded findings/references enter prompts; credentials never do. Structured outputs select only known finding IDs, review-question categories and a bounded executive focus. The server supplies the original finding statements and verified quotations. Unsupported finance claims, invented documents, changed readiness or extra fields fall back to templates. The model has no repository, Miro or approval-service capability.

Evaluations include malicious instructions and HTML-like content. Source quotations never confer authority. Free-form paraphrases that cannot be validated are rejected by design.

## External operations and secrets

Miro defaults to SQLite mock. Live initialisation requires both opt-in settings and an authorised OAuth token; publishing requires the configured board, synthetic project and current approval. Board creation is an adapter capability, never an automatic API action. No real Miro request has been made. Actual local Ollama inference was validated on 2026-11-11; see the live integration report.

Credentials remain in server environment variables, absent from browser bundles, domain persistence, prompts and logs. HTTP logs omit headers/body/query. Provider logs retain method/path/status only; error messages are redacted. Failures return generic text and correlation IDs. Audit persists approval/publication transitions and request outcomes.

Limits: one local process, JSON-backed SQLite, no production SSO, no signed audit log/retention policy, no remote drift checking or automated ambiguous-write recovery. Local database administration is trusted access. Production mode fails closed.
