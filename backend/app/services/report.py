from app.domain.models import GateAssessment, Project
from app.services.miro.scene import clean


def executive_report(a: GateAssessment, project: Project, value: dict) -> str:
    lines = [
        f"# {project.name} — Executive review",
        "",
        "**Entirely synthetic. Modelled benefits; no achieved savings or customer endorsement.**",
        "",
        "## 1. Executive summary",
        f"Gate 3 readiness: **{a.overall_readiness}**. {a.blocker_count} deterministic blockers; {a.warning_count} warnings. Human decisions remain mandatory.",
        "## 2. Manufacturing operating problem",
        "Fictional Northstar faces scattered quality records, inconsistent traceability, incomplete change validation and manual gate preparation.",
        "## 3. Gate readiness",
        f"Policy {a.policy_version}; assessment {a.id}, version {a.assessment_version}. Snapshot `{a.source_snapshot_hash}`. Review: {a.review_status}. READY_FOR_REVIEW never authorises production.",
        "## 4. Quality and validation risks",
    ]
    lines += [f"- {f.rule_id} [{f.category}]: {clean(f.message)}" for f in a.findings]
    lines += [
        "## 5. Evidence completeness",
        f"Validated coverage: {a.requirement_coverage}%. Only fully validated, uncontradicted evidence counts. Partial, missing and conflicting records contribute zero.",
    ]
    lines += [
        f"- {r.document_id} rev {r.revision} ({r.location}): “{clean(r.quote)}” [hash {r.content_hash[:12]}]"
        for r in a.evidence_references
    ]
    lines += ["## 6. Recommended corrective actions"]
    lines += [
        f"- {r['id']}: {r['title']}; owner {r['owner']}; due {r['due_date']}; {r['status']}."
        for r in a.source_records["action"]
        if r["status"] != "COMPLETE"
    ]
    lines += [
        "## 7. AI-enabled future workflow",
        "Ingest approved sources → deterministic rules → grounded explanation → human review → version-bound publication approval → explicit publication. AI has no action or launch authority.",
        "## 8. Financial scenarios and assumptions",
        value["method"],
        f"Baseline: {value['baseline']}",
        "| Scenario | Hours/year | Gross GBP | Net GBP | First-year net GBP | ROI % | Payback years |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {s['name']} | {s['annual_hours_saved']} | {s['annual_gross_benefit']} | {s['annual_net_benefit']} | {s['first_year_net_benefit']} | {s['first_year_roi_percent']} | {s['simple_payback_years']} |"
        for s in value["scenarios"]
    ]
    lines += [f"- {s['name']} inputs: {s['inputs']}" for s in value["scenarios"]]
    lines += [
        "## 9. Risks and limitations",
        "Synthetic source quality, adoption uncertainty and incomplete manufacturing validation limit conclusions. Local demo identity is non-production. Live Miro and optional LLM require separate validation. No defect-cost avoidance or revenue uplift is assumed.",
        "## 10. Validation Sprint outcomes and next-step proposal",
        "Software tests demonstrate the local mock workflow only. No customer sprint has occurred. Proposed next step: a hypothetical two-week evidence and value validation sprint, with sponsor-owned exit criteria, approved data access, measured preparation effort and human review sign-off. See docs/validation-sprint.md.",
        "",
        "Human decision log:",
    ]
    lines += [f"- {d.actor}: {d.decision}; {clean(d.note)} ({d.timestamp})" for d in a.decisions] or [
        "- No human review recorded."
    ]
    return "\n\n".join(lines) + "\n"
