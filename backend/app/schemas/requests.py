from typing import Literal
from pydantic import Field
from app.domain.models import Model, Role


class DemoLogin(Model):
    role: Role


class ReviewRequest(Model):
    decision: Literal["ACKNOWLEDGED", "CHANGES_REQUESTED"]
    note: str = Field(min_length=1, max_length=2000)


class ApprovalRequest(Model):
    action: Literal["request", "approve"]
    destination_board: str = Field(pattern=r"^[A-Za-z0-9_=:-]{1,100}$")


class PublishRequest(Model):
    approval_id: str
