from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from core.content.scoring import content_score
from core.db.models import (
    ExecutionMode,
    Member,
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


class FleetAgent(BaseModel):
    member_id: str
    display_name: str
    role: str
    provider: str
    model: Optional[str]
    runs: int
    tasks_owned: int
    avg_score: Optional[int]
    self_corrections: int


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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> Optional[dict]:
        """0–100 content score derived from the checks (None when not scoreable)."""
        return content_score(self.checks)


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


class TrendRefresh(BaseModel):
    campaign_id: str
    timely_angles: list[str]


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
    review_assets: bool = False
    with_visuals: bool = False

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

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("comment body cannot be empty")
        return cleaned


class MetricsRequest(BaseModel):
    impressions: int = 0
    clicks: int = 0
    signups: int = 0


class PostPerformance(BaseModel):
    post_id: str
    title: str
    url: str
    published_at: str
    publish_status: str = "draft"
    permalink: Optional[str] = None
    impressions: int
    clicks: int
    signups: int
    source: str


class PlatformPerformance(BaseModel):
    platform: str
    impressions: int
    clicks: int
    signups: int
    posts: list[PostPerformance]


class PerformanceData(BaseModel):
    campaign_id: str
    platforms: list[PlatformPerformance]
    totals: dict[str, int]
    note: str


# --- Org configuration (the per-tenant digital-employee roster) ---


class OrgMemberRead(BaseModel):
    id: str
    kind: MemberKind
    role: MemberRole
    display_name: str
    job_description: str
    reports_to: Optional[str]
    handles_kinds: list[str]
    # AI-only, surfaced from agent_config for the team view.
    agent_role: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

    @classmethod
    def from_member(cls, member: Member) -> "OrgMemberRead":
        config = member.agent_config or {}
        return cls(
            id=member.id,
            kind=member.kind,
            role=member.role,
            display_name=member.display_name,
            job_description=member.job_description,
            reports_to=member.reports_to,
            handles_kinds=member.handles_kinds or [],
            agent_role=config.get("role"),
            provider=config.get("provider"),
            model=config.get("model"),
        )


class AgentRoleRead(BaseModel):
    key: str
    title: str
    job_description: str


class OrgRead(BaseModel):
    members: list[OrgMemberRead]
    task_kinds: list[str]  # kinds a member can be set to handle
    agent_roles: list[AgentRoleRead]  # AI agents a digital employee can run as


class CreateOrgMemberRequest(BaseModel):
    """Add an AI digital employee. Humans are onboarded via auth/invite, later."""

    display_name: str
    role: str  # the agent role this employee runs as (an agent_roles key)
    job_description: str = ""
    handles_kinds: list[str] = []
    provider: str = "mock"
    model: Optional[str] = None
    reports_to: Optional[str] = None

    @field_validator("display_name")
    @classmethod
    def _non_empty_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("display_name cannot be empty")
        return cleaned


class UpdateOrgMemberRequest(BaseModel):
    """Reconfigure a digital employee. Every field is optional; omitted = unchanged."""

    job_description: Optional[str] = None
    handles_kinds: Optional[list[str]] = None
    reports_to: Optional[str] = None
    role: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
