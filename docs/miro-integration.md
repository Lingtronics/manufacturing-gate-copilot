# Miro integration and recovery

**Mock:** implemented and tested through API and Chromium. All writes stay in SQLite.

**Live:** REST v2 adapter implemented with HTTP transport tests. No real board was created, modified or demonstrated. Activation remains an explicit opt-in after human authorisation.

## Official references reviewed on 2026-10-24

- [REST overview / OAuth](https://developers.miro.com/reference/overview)
- [Create board](https://developers.miro.com/reference/create-board-1)
- [Bulk items](https://developers.miro.com/reference/create-items)
- [Rate limiting](https://developers.miro.com/reference/rate-limiting)
- [Frames](https://developers.miro.com/reference/create-frame-item)
- [Shapes](https://developers.miro.com/reference/create-shape-item-1) and [shape updates](https://developers.miro.com/reference/update-shape-item-1)
- [Sticky notes](https://developers.miro.com/reference/create-sticky-note-item-1)
- [Text](https://developers.miro.com/reference/create-text-item-1)
- [Connectors](https://developers.miro.com/reference/create-connector-1)
- [REST resource/update mapping](https://developers.miro.com/docs/rest-api-reference-guide)

Base URL is fixed to `https://api.miro.com/v2`. Use least-privilege `boards:read`/`boards:write`. Obtain consent through Miro's documented OAuth authorisation-code process. This MVP accepts a manually supplied valid OAuth token for local development; it has no hosted redirect/refresh UI. An arbitrary API key is not OAuth authorisation.

## Explicit live setup, only after authorisation

Use an existing authorised board and synthetic data only. Keep secrets in backend environment variables, never frontend `VITE_` settings.

```powershell
$env:MIRO_MODE = 'live'
$env:ALLOW_LIVE_MIRO = 'true'
$env:MIRO_BOARD_ID = '<authorised-existing-board-id>'
# Supply MIRO_OAUTH_TOKEN in the server environment via your secret manager.
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Adapter construction makes no request. Publication requires reviewer acknowledgement, publisher approval and a separate publish command. Destination must match the configured board. The board-creation adapter method is never invoked automatically.

## Type-specific contracts

| Scene type | REST resource, with PATCH resource/{id} for updates | Distinct data |
|---|---|---|
| Section | `frames` | title/freeform and width/height |
| Shape | `shapes` | rectangle content, fill colour, width/height |
| Sticky | `sticky_notes` | square content, named fill, width only |
| Text | `texts` | content/width; dynamic height |
| Connector | `connectors` | resolved start/end IDs and elbowed shape |

Generated boards use frames, shapes and connectors. Text/sticky serializers are supported. Unknown operations fail explicitly. Content is escaped and stable keys map to returned IDs.

The documented bulk endpoint supports at most 20 items. Adapter calls reject larger lists. This implementation uses individual creates so each mutation has its own durable journal/mapping, without assuming bulk response order. Frames and connectors use their distinct resources. Bulk execution has not been validated or claimed.

## Reconciliation and bounded failure

Mappings are namespaced by mode/board/stable key. Unchanged hashes preserve IDs; changed payloads update known IDs; new keys create. Unrelated objects are untouched. Removed keys are retained and counted as `retained_stale`; the app never clears a board. After reconciliation, live publication now reads managed objects back and compares their fields with the approved scene. Missing or changed managed content fails verification. It does not silently recreate a missing remote object.

HTTP timeout: ten seconds. At most three attempts for safe reads/updates and explicit 429 rejection. Retry-After over two seconds defers to a later retry. Timeout/5xx/malformed create responses are ambiguous and never replayed blindly. Secrets and raw provider responses are never logged.

Each mutation persists STARTED, then SUCCEEDED/FAILED/AMBIGUOUS. Known partial failure preserves successful mappings; retry adds only missing items. Prior STARTED/AMBIGUOUS blocks automatic retry for that item. Persistent PUBLISHING blocks further publication after a crash.

## Manual recovery runbook

1. Stop attempts and retain the database/audit trail.
2. As Publisher, inspect `/api/v1/publication-operations`, mappings and the intended board.
3. Verify whether the ambiguous item exists and matches its stable key/content. Do not guess or clear a board.
4. A trusted local administrator reconciles a verified remote ID into its mapping and marks the operation SUCCEEDED, or marks a provably absent operation FAILED. Verify remote results before marking stale PUBLISHING as FAILED for controlled retry.
5. Record recovery actor/evidence in audit, re-preview, request fresh approval if content changed, and explicitly republish.

There is no blind one-click recovery override. Guided recovery remains v1.1 work; publication read-back verification is now implemented.

## Separate live validation

After authorisation: confirm scopes/board; preview synthetic content; review/approve/publish; inspect frames/content/connectors on Miro; republish and compare IDs; verify an unrelated manual note survives; change scene and obtain fresh approval; inspect failures/audit. None of these real-Miro steps is claimed complete.


## 2026-11-11 implementation update

See [live integration validation](live-integration-validation.md) for the new `miro-read` and `miro-publication` commands, required credentials/approval IDs and exact evidence. Read-back uses each documented type-specific GET route, plus cursor-paginated regular-item and connector listings. The official [Miro OpenAPI](https://github.com/miroapp/api-clients/blob/main/packages/generator/spec.json) was fetched and inspected for request/response field differences. Live validation is still BLOCKED by missing board/token, not reported as passed from transport tests.
