"""SQLModel ORM entities for the human-AI team OS slice.

All tenant-owned rows carry ``tenant_id`` for row-level isolation. Importing
this module registers every table on ``SQLModel.metadata`` so ``init_db()``
can create them.

Relationships are intentionally modelled as plain foreign-key id columns (no
ORM ``Relationship``) to keep the slice simple and session-handling explicit;
the service layer joins by querying ids.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MemberKind(str, Enum):
    HUMAN = "human"
    AI = "ai"


class MemberRole(str, Enum):
    LEAD = "lead"
    MEMBER = "member"


class TaskKind(str, Enum):
    IDEATION = "ideation"
    PLANNING = "planning"
    ASSET = "asset"
    VISUAL = "visual"
    CLAIM_CHECK = "claim_check"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    NEEDS_REVIEW = "needs_review"
    DONE = "done"
    BLOCKED = "blocked"


class ExecutionMode(str, Enum):
    AI_DRAFT_HUMAN_REVIEW = "ai_draft_human_review"
    AI_AUTO = "ai_auto"
    HUMAN_ONLY = "human_only"


class TaskEventType(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    EDITED = "edited"
    COMMENTED = "commented"
    STATUS_CHANGED = "status_changed"
    AI_RUN = "ai_run"
    SELF_CORRECTED = "self_corrected"


class Tenant(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=_now)


class User(SQLModel, table=True):
    # "app_user" avoids the reserved word "user" on engines like PostgreSQL.
    __tablename__ = "app_user"

    id: str = Field(default_factory=_uuid, primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    created_at: datetime = Field(default_factory=_now)


class Member(SQLModel, table=True):
    """A worker in a tenant — either a human (links to a User) or an AI agent.

    The org is configured per tenant on the members themselves: ``job_description``
    is the digital employee's charter, ``reports_to`` is their manager (a member in
    the same tenant), and ``handles_kinds`` are the task kinds they are the default
    owner of — which is what routes work to them, instead of a hardcoded table.
    For an AI member, ``agent_config["role"]`` names the agent that runs their work.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    kind: MemberKind
    role: MemberRole = MemberRole.MEMBER
    display_name: str
    job_description: str = ""
    reports_to: Optional[str] = Field(default=None, foreign_key="member.id")
    handles_kinds: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    user_id: Optional[str] = Field(default=None, foreign_key="app_user.id")
    agent_config: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class Campaign(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    name: str
    template: str = "general"
    brief: dict = Field(sa_column=Column(JSON, nullable=False))
    status: str = "active"
    event_name: Optional[str] = None
    event_date: Optional[str] = None  # ISO date "YYYY-MM-DD" the campaign anchors on
    created_by: Optional[str] = Field(default=None, foreign_key="member.id")
    created_at: datetime = Field(default_factory=_now)


class Task(SQLModel, table=True):
    """A unit of work in a campaign, assignable to a human or an AI member.

    ``ai_draft`` keeps the immutable original AI output; ``output`` holds the
    current (possibly human-edited) version. Their diff is the future learning
    signal. Both store one of the existing Pydantic schemas as JSON.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    kind: TaskKind
    title: str
    status: TaskStatus = TaskStatus.TODO
    execution_mode: ExecutionMode = ExecutionMode.AI_DRAFT_HUMAN_REVIEW
    assignee_id: Optional[str] = Field(default=None, foreign_key="member.id")
    depends_on: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    sequence: int = 0
    ai_draft: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    output: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    params: dict = Field(default_factory=dict, sa_column=Column(JSON))
    checks: dict = Field(default_factory=dict, sa_column=Column(JSON))
    due_date: Optional[str] = None  # ISO date the task is scheduled for
    phase: Optional[str] = None  # prep | warmup | buildup | prelaunch | launch | followup
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Comment(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    task_id: str = Field(index=True, foreign_key="task.id")
    author_id: str = Field(foreign_key="member.id")
    body: str
    created_at: datetime = Field(default_factory=_now)


class TaskEvent(SQLModel, table=True):
    """Audit trail entry. Approve/edit/reject rows seed the Phase 3 learning loop."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    task_id: str = Field(index=True, foreign_key="task.id")
    actor_id: Optional[str] = Field(default=None, foreign_key="member.id")
    type: TaskEventType
    payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class UsageEvent(SQLModel, table=True):
    """Metering for future billing — one row per AI task run."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    task_id: Optional[str] = Field(default=None, foreign_key="task.id")
    member_id: Optional[str] = Field(default=None, foreign_key="member.id")
    kind: str = "ai_task_run"
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens: Optional[int] = None
    created_at: datetime = Field(default_factory=_now)


class BrandProfile(SQLModel, table=True):
    """Persistent, tenant-level brand identity applied across all campaigns.

    One per tenant; this is what makes tone and proof consistent across events,
    not just within one campaign.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, unique=True, foreign_key="tenant.id")
    voice: str = ""
    tone_rules: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    forbidden_words: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    approved_phrases: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    proof_points: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class ContentAtom(SQLModel, table=True):
    """A reusable named content block harvested from an approved asset.

    Persisted per tenant so atoms can be reused across campaigns (events).
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    kind: str  # headline | hook | cta | proof | one_liner
    text: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_campaign_id: Optional[str] = Field(default=None, foreign_key="campaign.id")
    source_task_id: Optional[str] = Field(default=None, foreign_key="task.id")
    created_at: datetime = Field(default_factory=_now)


class Milestone(SQLModel, table=True):
    """A dated phase in a campaign's back-planned schedule (calendar backbone)."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    phase: str  # warmup | buildup | prelaunch | launch | followup
    name: str
    date: str  # ISO date
    offset_days: int  # relative to the event date
    objective: str = ""
    created_at: datetime = Field(default_factory=_now)


class Post(SQLModel, table=True):
    """A published instance of an asset on a specific platform.

    ``url`` is the UTM-tagged destination; the publish_* fields track the actual
    delivery to a channel through a swappable PublishProvider (mock until a real
    provider is connected). ``permalink`` is the public post URL once it is live.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    asset_task_id: str = Field(index=True, foreign_key="task.id")
    platform: str
    url: str
    published_at: str  # ISO date
    publish_provider: str = "none"
    publish_status: str = "draft"  # draft | scheduled | published | failed
    external_id: Optional[str] = None
    permalink: Optional[str] = None
    publish_error: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class MetricSnapshot(SQLModel, table=True):
    """A point-in-time performance reading for a published post."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    post_id: str = Field(index=True, foreign_key="post.id")
    source: str = "manual"  # manual | website | esp | github | ...
    impressions: int = 0
    clicks: int = 0
    signups: int = 0
    captured_at: datetime = Field(default_factory=_now)


class EpisodicNote(SQLModel, table=True):
    """Episodic memory: a campaign-level decision or lead-feedback note that later
    work reads, so the team's choices accumulate across tasks (and, later, campaigns).
    Semantic memory = BrandProfile; working memory = the task context."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    kind: str = "feedback"  # feedback | decision | summary
    text: str
    created_at: datetime = Field(default_factory=_now)
