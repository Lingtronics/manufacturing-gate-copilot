from decimal import Decimal
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.utils import now


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criticality(StrEnum):
    CRITICAL = "CRITICAL"
    STANDARD = "STANDARD"


class EvidenceStatus(StrEnum):
    VALIDATED = "VALIDATED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"


class IssueSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class ChangeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    VALIDATED = "VALIDATED"


class Readiness(StrEnum):
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONDITIONAL_REVIEW = "CONDITIONAL_REVIEW"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"


class ReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    ASSESSED = "ASSESSED"
    REVIEWED = "REVIEWED"


class PublicationStatus(StrEnum):
    PREVIEW = "PREVIEW"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class Role(StrEnum):
    ANALYST = "Analyst"
    REVIEWER = "Reviewer"
    PUBLISHER = "Publisher"


class Project(Model):
    id: str
    name: str
    gate_id: str
    synthetic: bool = True
    participants: list[str]


class GateDefinition(Model):
    id: str
    name: str
    policy_version: str
    policy_document_id: str
    required_requirement_ids: list[str]
    rules: dict[str, str]


class GateRequirement(Model):
    id: str
    project_id: str
    title: str
    criteria: str
    criticality: Criticality
    mandatory: bool = True
    evidence_ids: list[str]
    expected_classification: EvidenceStatus


class EvidenceDocument(Model):
    id: str
    revision: str
    source_type: Literal["markdown", "json"]
    title: str
    source_text: str
    requirement_ids: list[str]
    location: str
    content_hash: str
    evidence_status: EvidenceStatus
    expected_classification: str


class EvidenceReference(Model):
    id: str
    document_id: str
    revision: str
    location: str
    quote: str = Field(min_length=1)
    content_hash: str


class QualityIssue(Model):
    id: str
    project_id: str
    title: str
    requirement_ids: list[str]
    evidence_ids: list[str]
    severity: IssueSeverity
    resolved: bool
    expected_classification: str


class EngineeringChange(Model):
    id: str
    project_id: str
    title: str
    requirement_ids: list[str]
    evidence_ids: list[str]
    status: ChangeStatus
    validation_complete: bool
    expected_classification: str

    @model_validator(mode="after")
    def consistent(self) -> "EngineeringChange":
        if self.status == ChangeStatus.VALIDATED and not self.validation_complete:
            raise ValueError("Validated changes require completed validation")
        return self


class CorrectiveAction(Model):
    id: str
    project_id: str
    issue_id: str
    title: str
    owner: str
    due_date: str
    status: ActionStatus
    blocking: bool
    expected_classification: str


class AssessmentFinding(Model):
    id: str
    rule_id: str
    category: Literal["blocker", "insufficient", "warning"]
    requirement_ids: list[str]
    record_id: str
    message: str
    evidence_references: list[EvidenceReference] = []
    provenance: Literal["deterministic"] = "deterministic"


class ReviewDecision(Model):
    id: str
    assessment_id: str
    assessment_version: int
    actor: str
    decision: Literal["ACKNOWLEDGED", "CHANGES_REQUESTED"]
    note: str = Field(min_length=1, max_length=2000)
    timestamp: str = Field(default_factory=now)


class GateAssessment(Model):
    id: str
    project_id: str
    policy_version: str
    source_snapshot_hash: str
    assessment_version: int
    overall_readiness: Readiness
    requirement_coverage: Decimal
    blocker_count: int
    warning_count: int
    findings: list[AssessmentFinding]
    evidence_references: list[EvidenceReference]
    generated_at: str = Field(default_factory=now)
    review_status: ReviewStatus = ReviewStatus.ASSESSED
    requirement_states: dict[str, EvidenceStatus]
    decisions: list[ReviewDecision] = []
    source_records: dict[str, list[dict]]


class PublicationApproval(Model):
    id: str
    assessment_id: str
    assessment_version: int
    scene_content_hash: str
    actor: str
    destination_board: str = Field(pattern=r"^[A-Za-z0-9_=:-]{1,100}$")
    timestamp: str = Field(default_factory=now)
    status: PublicationStatus


class MiroPublication(Model):
    id: str
    assessment_id: str
    approval_id: str
    destination_board: str
    status: PublicationStatus
    mode: Literal["mock", "live"]
    scene_content_hash: str
    board_url: str | None = None
    result: dict = {}
    timestamp: str = Field(default_factory=now)


class KpiBaseline(Model):
    id: str
    project_id: str
    evidence_collection_hours: Decimal = Field(ge=0)
    preparation_hours: Decimal = Field(ge=0)
    annual_reviews: int = Field(ge=0)
    labour_cost_per_hour: Decimal = Field(ge=0)
    gate_cycle_days: Decimal = Field(ge=0)
    evidence_coverage: Decimal = Field(ge=0, le=1)
    defect_recurrence: Decimal | None = Field(default=None, ge=0, le=1)
    currency: Literal["GBP"] = "GBP"
    synthetic: bool = True


class ValueScenario(Model):
    id: str
    name: str
    assumption_version: str
    preparation_reduction: Decimal = Field(ge=0, le=1)
    collection_reduction: Decimal = Field(ge=0, le=1)
    implementation_cost: Decimal = Field(ge=0)
    annual_operating_cost: Decimal = Field(ge=0)
    adoption_rate: Decimal = Field(ge=0, le=1)
    annual_review_volume: int = Field(ge=0)


class AuditEvent(Model):
    id: str
    actor: str
    event: str
    entity_id: str
    correlation_id: str
    details: dict = {}
    timestamp: str = Field(default_factory=now)
