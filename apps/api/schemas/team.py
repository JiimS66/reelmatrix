from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from core.db.models import (
    ExecutionMode,
    MemberKind,
    MemberRole,
    TaskEventType,
    TaskKind,
    TaskStatus,
)


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: MemberKind
    role: MemberRole
    display_name: str


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    kind: TaskKind
    title: str
    status: TaskStatus
    execution_mode: ExecutionMode
    assignee_id: Optional[str]
    depends_on: list[str]
    sequence: int
    params: dict
    output: Optional[dict]
    checks: dict
    due_date: Optional[str]
    phase: Optional[str]
    updated_at: datetime


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    body: str
    created_at: datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: TaskEventType
    actor_id: Optional[str]
    payload: Optional[dict]
    created_at: datetime


class AtomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    text: str
    tags: list[str]
    source_campaign_id: Optional[str]
    created_at: datetime


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    template: str
    status: str
    event_name: Optional[str]
    event_date: Optional[str]


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phase: str
    name: str
    date: str
    offset_days: int
    objective: str


class BoardRead(BaseModel):
    campaign: CampaignRead
    tasks: list[TaskRead]
    members: list[MemberRead]


class ScheduleRead(BaseModel):
    campaign: CampaignRead
    milestones: list[MilestoneRead]
    tasks: list[TaskRead]
    timely_angles: list[str]


class TodoItem(BaseModel):
    campaign_name: str
    task: TaskRead


class TaskDetailRead(BaseModel):
    task: TaskRead
    ai_draft: Optional[dict]
    comments: list[CommentRead]
    events: list[EventRead]
    available_actions: list[str]


class CreateCampaignRequest(BaseModel):
    name: str
    brief: dict
    template: str = "general"
    event_name: Optional[str] = None
    event_date: Optional[str] = None

    @field_validator("event_date")
    @classmethod
    def _valid_event_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("event_date must be an ISO date (YYYY-MM-DD)") from exc
        return value


class AssignRequest(BaseModel):
    member_id: Optional[str] = None
    execution_mode: Optional[ExecutionMode] = None


class SubmitRequest(BaseModel):
    output: Optional[dict] = None


class EditRequest(BaseModel):
    output: dict


class ReviewRequest(BaseModel):
    action: Literal["approve", "request_changes"]
    output: Optional[dict] = None
    note: Optional[str] = None


class CommentRequest(BaseModel):
    body: str
