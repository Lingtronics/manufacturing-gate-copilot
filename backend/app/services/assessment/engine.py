from decimal import Decimal
from app.core.utils import uid
from app.domain.models import (
    GateAssessment,
    AssessmentFinding,
    EvidenceStatus,
    GateRequirement,
    QualityIssue,
    EngineeringChange,
    CorrectiveAction,
    Criticality,
    Readiness,
)
from app.services.evidence.index import EvidenceIndex, snapshot_hash


def assess(records: dict, version: int = 1) -> GateAssessment:
    index = EvidenceIndex(records["evidence"])
    requirements = [GateRequirement.model_validate(r) for r in records["requirement"]]
    gate = records["gate"][0]
    if {r.id for r in requirements} != set(gate["required_requirement_ids"]):
        raise ValueError("Policy requirement set does not match source records")
    findings: list[AssessmentFinding] = []
    states: dict[str, EvidenceStatus] = {}
    critical_ids = {r.id for r in requirements if r.criticality == Criticality.CRITICAL}

    def add(rule, category, rid, reqs, message, docs):
        refs = [
            index.reference(d)
            for did in docs
            for d in index.exact(did)
            if d.evidence_status != EvidenceStatus.MISSING
        ]
        if not all(index.validate(r) for r in refs):
            raise ValueError("Unverifiable citation")
        findings.append(
            AssessmentFinding(
                id=f"F-{rule}-{rid}",
                rule_id=rule,
                category=category,
                requirement_ids=reqs,
                record_id=rid,
                message=message,
                evidence_references=refs,
            )
        )

    for req in requirements:
        docs = [d for did in req.evidence_ids for d in index.exact(did)]
        missing = not req.evidence_ids or any(
            not index.exact(did) or any(d.evidence_status == EvidenceStatus.MISSING for d in index.exact(did))
            for did in req.evidence_ids
        )
        conflict = any(
            len({d.content_hash for d in index.exact(did)}) > 1 for did in req.evidence_ids
        ) or any(d.evidence_status == EvidenceStatus.CONFLICTING for d in docs)
        partial = any(d.evidence_status == EvidenceStatus.PARTIAL for d in docs)
        linked = all(req.id in d.requirement_ids for d in docs)
        state = (
            EvidenceStatus.CONFLICTING
            if conflict
            else EvidenceStatus.MISSING
            if missing
            else EvidenceStatus.PARTIAL
            if partial or not linked
            else EvidenceStatus.VALIDATED
        )
        states[req.id] = state
        if state == EvidenceStatus.CONFLICTING:
            add(
                "GATE-004",
                "insufficient",
                req.id,
                [req.id],
                f"{req.id}: active supporting evidence conflicts; reconcile revisions.",
                req.evidence_ids,
            )
        elif state == EvidenceStatus.MISSING and req.criticality == Criticality.CRITICAL:
            add(
                "GATE-001",
                "blocker",
                req.id,
                [req.id],
                f"{req.id}: critical evidence missing.",
                req.evidence_ids,
            )
        elif state != EvidenceStatus.VALIDATED and req.mandatory:
            add(
                "GATE-006",
                "insufficient",
                req.id,
                [req.id],
                f"{req.id}: mandatory validated source unavailable ({state}).",
                req.evidence_ids,
            )
        elif state != EvidenceStatus.VALIDATED:
            add(
                "GATE-005",
                "warning",
                req.id,
                [req.id],
                f"{req.id}: optional supporting evidence incomplete.",
                req.evidence_ids,
            )
    for raw in records["issue"]:
        issue = QualityIssue.model_validate(raw)
        if not issue.resolved and issue.severity in ["HIGH", "CRITICAL"]:
            add(
                "GATE-002",
                "blocker",
                issue.id,
                issue.requirement_ids,
                f"{issue.id}: {issue.title} remains unresolved ({issue.severity}).",
                issue.evidence_ids,
            )
    for raw in records["change"]:
        change = EngineeringChange.model_validate(raw)
        if not change.validation_complete:
            add(
                "GATE-003",
                "blocker" if critical_ids.intersection(change.requirement_ids) else "warning",
                change.id,
                change.requirement_ids,
                f"{change.id}: {change.title}; validation incomplete.",
                change.evidence_ids,
            )
    for raw in records["action"]:
        action = CorrectiveAction.model_validate(raw)
        if action.status != "COMPLETE" and not action.blocking:
            add(
                "GATE-005",
                "warning",
                action.id,
                [],
                f"{action.id}: {action.title}; owner {action.owner}, due {action.due_date}.",
                [],
            )
    blockers = sum(f.category == "blocker" for f in findings)
    warnings = sum(f.category == "warning" for f in findings)
    insufficient = any(f.category == "insufficient" for f in findings)
    readiness = (
        Readiness.NOT_READY
        if blockers
        else Readiness.INSUFFICIENT_EVIDENCE
        if insufficient
        else Readiness.CONDITIONAL_REVIEW
        if warnings
        else Readiness.READY_FOR_REVIEW
    )
    mandatory = [r for r in requirements if r.mandatory]
    coverage = (
        Decimal(sum(states[r.id] == EvidenceStatus.VALIDATED for r in mandatory))
        * 100
        / Decimal(len(mandatory))
        if mandatory
        else Decimal(100)
    )
    refs = {r.id: r for f in findings for r in f.evidence_references}
    for req in requirements:
        for did in req.evidence_ids:
            for d in index.exact(did):
                if d.evidence_status != EvidenceStatus.MISSING:
                    ref = index.reference(d)
                    refs[ref.id] = ref
    return GateAssessment(
        id=uid("ASM"),
        project_id=records["project"][0]["id"],
        policy_version=gate["policy_version"],
        source_snapshot_hash=snapshot_hash(records),
        assessment_version=version,
        overall_readiness=readiness,
        requirement_coverage=coverage.quantize(Decimal("0.01")),
        blocker_count=blockers,
        warning_count=warnings,
        findings=findings,
        evidence_references=list(refs.values()),
        requirement_states=states,
        source_records=records,
    )
