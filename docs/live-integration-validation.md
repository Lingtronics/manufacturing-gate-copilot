# Live integration validation — 2026-11-11

## Results

| Integration | Result | Evidence |
|---|---|---|
| Ollama runtime | INSTALLED | Official winget package Ollama.Ollama 0.40.16; installer hash verified |
| Local model | VALIDATED | llama3.2:1b downloaded and verified by Ollama |
| Actual inference | PASSED | Baseline and prompt-injection cases both returned model_used; 13 grounded findings; NOT_READY unchanged |
| Application model path | PASSED | Real Chromium test confirmed the model output reaches Gate Assessment and is cached |
| Miro adapter/read-back | IMPLEMENTED / TRANSPORT-TESTED | Typed routes, bounded pagination, remote-ID/content read-back, drift detection, approval-bound validation command |
| Actual Miro publication | BLOCKED | No authorised test board or MIRO_OAUTH_TOKEN supplied; no real Miro request made |
| Docker runtime | UNVALIDATED | Docker is unavailable on this host; outside the Ollama installation authorisation |

Actual evidence: [model validation JSON](ollama-live-validation.json), [real model browser log](ollama-browser-validation.log), [final backend log](integration-backend-final.log), [offline build/type/lint/browser log](integration-upgrade-verification.log), [Miro preflight result](miro-live-validation.json).

The first Ollama validation used about 8.3 seconds for the baseline and 2.6 seconds for the injection case. Both used real inference, not template fallback. The final backend suite has **61 passing tests**, the offline browser suite has **2 passing tests**, and the separate live Ollama browser suite has **1 passing test**. Ruff, mypy (29 app files), Prettier and the production build passed. An upstream Starlette/AnyIO deprecation warning remains.

## What changed

The model now returns a small schema containing known finding IDs, bounded review-question categories and an executive focus. Dynamic schema constraints enumerate permitted IDs and require the exact finding count. Duplicate/missing IDs and unsupported fields are rejected. The server renders the original deterministic finding statements and verified citations. This reduces copying errors and token cost while preserving authority boundaries.

Responses expose model name, latency, model_used/fallback state and a safe fallback reason. The UI displays those states and the selected review sequence. Only successful validated model results are cached for the exact assessment/model/contract. Fallback is never counted as a successful live-provider check. Runtime request timeout defaults to 30 seconds, configurable from 1 to 60; connection timeout is two seconds. The model has no action tools or credential access.

Live Miro publication now reads each managed item back and compares its identity and managed fields with the approved scene. HTML/number formatting is normalised; changed remote content fails verification rather than claiming success. Bounded pagination reads both regular items and connectors. The explicit publication validator checks first publication, unchanged republish, stable IDs, verified content and unrelated-item preservation. It uses an existing application approval and does not manufacture a human review or approval.

## Run the validated local provider

```powershell
./scripts/start.ps1 -Ollama
```

This opts the current process into Ollama. Defaults without that switch still use deterministic templates. The installed model is llama3.2:1b. Ollama runs at http://127.0.0.1:11434. No API key is needed.

Reproduce actual inference and the browser check (stop a manually running app on port 8000 before the browser command):

```powershell
.venv/Scripts/python.exe scripts/validate_integrations.py ollama --model llama3.2:1b --output docs/ollama-live-validation.json
npm.cmd run test:live:ollama --prefix frontend
```

Neither command installs/downloads a model automatically. The CLI exits nonzero on fallback or incomplete validation and overwrites a previous success artifact with a failure result.

Official references: [Ollama Windows](https://docs.ollama.com/windows), [local model](https://ollama.com/library/llama3.2:1b), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [chat API](https://docs.ollama.com/api/chat).

## What is still needed for Miro

1. A test-board URL or ID and permission to add/update the synthetic Northstar managed content on it. Your account must be able to edit the board.
2. A valid authorised OAuth access token with boards:read and boards:write, provided only in the local server environment as MIRO_OAUTH_TOKEN. Do not paste it into chat, logs or source files. A generic API key is insufficient.
3. The server launched with MIRO_MODE=live, ALLOW_LIVE_MIRO=true and MIRO_BOARD_ID set to that board. An Analyst creates the assessment, a Reviewer acknowledges it, and a Publisher requests and approves the exact scene before the explicit publish step.

A minimal board-access check does no writes:

```powershell
.venv/Scripts/python.exe scripts/validate_integrations.py miro-read --board '<board URL or ID>' --output docs/miro-live-validation.json
```

After review/approval, run the explicit live publication check with the returned IDs:

```powershell
.venv/Scripts/python.exe scripts/validate_integrations.py miro-publication --board '<board URL or ID>' --assessment-id '<assessment ID>' --approval-id '<approved publication ID>' --output docs/miro-live-validation.json
```

The CLI and server both require the intended board and explicit live configuration. The CLI signs in only as the local demo Publisher; it cannot bypass missing review or approval. It publishes twice to test idempotency and retains remote content. For a meaningful unrelated-content test, leave one existing manual test note on the board; the result records how many unrelated items were checked. It reports the count even when the board was initially empty.

A full changed-scene test still requires a new human-approved scene. Forced rate-limit/ambiguous-transport failures remain mocked; they are not deliberately induced against a live service. No hosted OAuth redirect/refresh UI is included; manual authorised token input is supported. See [Miro runbook](miro-integration.md).
