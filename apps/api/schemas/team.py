from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

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


class BoardRead(BaseModel):
    campaign: CampaignRead
    tasks: list[TaskRead]
    members: list[MemberRead]


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
