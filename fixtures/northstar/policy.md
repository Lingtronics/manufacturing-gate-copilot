# Synthetic Gate 3 policy v1.0

All fifteen requirements are mandatory. REQ-001, REQ-002 and REQ-003 are critical.

Only VALIDATED evidence with no conflicting active revisions counts toward coverage. PARTIAL, MISSING and CONFLICTING count as zero. Every listed source is required. Different active revisions are unresolved until a human reconciles them; no automatic latest-revision selection.

Unresolved HIGH or CRITICAL issues block review. Incomplete engineering validation blocks critical requirements and warns for standard requirements. Missing critical evidence blocks; missing mandatory non-critical evidence prevents assessment.

Blocking corrective actions must have an unresolved HIGH or CRITICAL issue; otherwise ingestion fails. Non-blocking open actions warn. READY_FOR_REVIEW authorises human review only, never production.
