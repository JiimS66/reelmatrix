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
    pillar_id: Optional[str] = Field(default=None, foreign_key="pillarasset.id")  # hub-spoke
    locked: bool = False  # proofing sign-off: output is immutable until unlocked
    locked_version_id: Optional[str] = Field(default=None, foreign_key="contentversion.id")
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Comment(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    task_id: str = Field(index=True, foreign_key="task.id")
    author_id: str = Field(foreign_key="member.id")
    body: str
    created_at: datetime = Field(default_factory=_now)


class ContentVersion(SQLModel, table=True):
    """An immutable snapshot of a task's output — the version stack behind proofing.

    Appended (never updated) on every output change, so reviewers can see history and
    a lock can pin the approved version. ``ai_draft`` is effectively the first version.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    task_id: str = Field(index=True, foreign_key="task.id")
    number: int  # 1, 2, 3… per task
    snapshot: dict = Field(sa_column=Column(JSON))
    source: str = "edit"  # ai_render | submit | edit | review_edit
    created_by: Optional[str] = Field(default=None, foreign_key="member.id")
    created_at: datetime = Field(default_factory=_now)


class Annotation(SQLModel, table=True):
    """A pinpoint/region/text-span comment anchored to a task's content — targeted
    feedback that resolves, distinct from the task-level Comment thread. ``anchor``
    holds normalized coordinates / a text quote so it survives a re-render."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    task_id: str = Field(index=True, foreign_key="task.id")
    author_id: str = Field(foreign_key="member.id")
    target: str = "general"  # general | text | region | timecode
    anchor: dict = Field(default_factory=dict, sa_column=Column(JSON))
    body: str
    resolved: bool = False
    resolved_by: Optional[str] = Field(default=None, foreign_key="member.id")
    created_at: datetime = Field(default_factory=_now)


class DirectMessage(SQLModel, table=True):
    """A message in the lead's direct line to a team member — chat + directives.
    AI members auto-reply in their role; the thread is the lead's 1:1 with them."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    member_id: str = Field(index=True, foreign_key="member.id")  # the employee this thread is with
    sender: str = "lead"  # lead | agent
    kind: str = "message"  # message | directive
    title: Optional[str] = None  # for a directive (assigned task)
    task_id: Optional[str] = Field(default=None, foreign_key="task.id")  # directive → tracked task
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
    # ICP library: who the brand sells to. Each segment =
    # {name, description, platforms[], pain_points[], reach_tactics[]}. A campaign
    # targets a subset (brief["target_segments"]); each post is routed to one.
    segments: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    # Persistent brand narrative (Phase 7): the messaging pyramid that spans every
    # campaign — a value proposition over a few messaging pillars. term_bank lives in
    # BrandTerm. Each pillar = {name, proof_points[]}.
    value_proposition: str = ""
    messaging_pillars: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class BrandTerm(SQLModel, table=True):
    """A typed terminology rule — the richer governance layer above
    ``BrandProfile.forbidden_words``. ``avoid`` terms are flagged (with a preferred
    ``replacement`` to suggest); ``use_carefully`` terms are flagged for a human
    double-check; ``approved`` terms document the house style."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    term: str
    term_type: str = "avoid"  # approved | avoid | use_carefully
    replacement: Optional[str] = None  # preferred swap for an avoid term
    case_sensitive: bool = False
    note: str = ""
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


class AttributeOutcome(SQLModel, table=True):
    """Derived (4th-layer) memory: a learned Beta(alpha, beta) posterior of conversion
    for ONE content attribute, sliced by channel and segment. Rebuilt from published
    posts + their MetricSnapshots by the OutcomeLearner — this is what turns the
    system's self-CORRECTION into outcome-LEARNING. A blank ``channel``/``segment``
    means the global (cold-start) prior across that dimension."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    attribute_type: str  # hook_type | cta_style | length_bucket | ...
    attribute_value: str
    channel: str = ""  # "" = across all channels
    segment: str = ""  # "" = across all segments
    impressions: int = 0
    conversions: int = 0
    n_posts: int = 0
    alpha: float = 1.0  # Beta posterior: 1 + conversions
    beta: float = 1.0  # Beta posterior: 1 + (impressions - conversions)
    updated_at: datetime = Field(default_factory=_now)


class Experiment(SQLModel, table=True):
    """A content experiment: variants of one brief that differ by tagged attributes,
    raced on conversion (GrowthBook/PostHog-style). Winners become reusable
    WinningPatterns — the ledger half of the flywheel."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    hypothesis: str
    channel: str = ""
    segment: str = ""
    stats_method: str = "bayesian"  # bayesian | frequentist (provider-swappable)
    status: str = "running"  # running | decided
    created_at: datetime = Field(default_factory=_now)
    decided_at: Optional[datetime] = None


class ExperimentVariant(SQLModel, table=True):
    """One arm of an experiment — exactly one per experiment has key=='control'. Carries
    the tagged attribute set (the shared vocabulary) + its draft + accumulated metrics +
    the decided result."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    experiment_id: str = Field(index=True, foreign_key="experiment.id")
    key: str  # control | A | B | C
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSON))
    content: dict = Field(default_factory=dict, sa_column=Column(JSON))
    rationale: str = ""
    impressions: int = 0
    conversions: int = 0
    chance_to_beat_control: float = 0.0
    result_status: str = "untested"  # untested | control | winner | loser | inconclusive


class WinningPattern(SQLModel, table=True):
    """A proven attribute combo promoted from a decided experiment — an experiment-backed
    generative prior injected into agent context alongside the flywheel memo. This is the
    agentic differentiator: a winner isn't just stored data, it becomes a generation rule."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSON))
    channel: str = ""
    segment: str = ""
    lift: float = 0.0  # relative CVR lift over the control
    confidence: float = 0.0  # chance-to-beat-control at decision time
    evidence_experiment_id: str = Field(foreign_key="experiment.id")
    created_at: datetime = Field(default_factory=_now)


class IncrementalityTest(SQLModel, table=True):
    """Phase 11 — a causal lift measurement (mock GeoHoldout; GeoLift/CausalImpact later).
    The flywheel learns CORRELATION; this measures the COUNTERFACTUAL and yields a
    multiplier that de-biases the Beta update — a high-converting attribute with LOW
    incrementality (just shown to high-intent audiences) gets shrunk toward baseline."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    attribute_type: str
    attribute_value: str
    naive_conversions: int = 0
    incremental_conversions: int = 0
    multiplier: float = 1.0  # incremental / naive — scales the attribute's win pseudo-count
    lift_pct: float = 0.0
    status: str = "measured"
    created_at: datetime = Field(default_factory=_now)


class DiscoveredSegmentCandidate(SQLModel, table=True):
    """A data-surfaced audience cluster proposed for promotion to a tracked ICP segment
    (Phase 6). Mock discovery now (a high-converting sub-cluster of a validated segment);
    HDBSCAN over behavioral features later. Promotion adds it to BrandProfile.segments."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    name: str
    rationale: str
    evidence: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = "pending"  # pending | promoted | dismissed
    created_at: datetime = Field(default_factory=_now)


class PillarAsset(SQLModel, table=True):
    """A long-form source asset (research doc, transcript, webinar) that atomizes into
    many channel posts — the hub of a hub-and-spoke content graph (HubSpot Content
    Remix). Derivative asset Tasks carry pillar_id back to it, inheriting its terms."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    title: str
    kind: str = "doc"  # doc | transcript | webinar
    source_text: str
    created_at: datetime = Field(default_factory=_now)


class OutboundProspect(SQLModel, table=True):
    """A scaled-but-1:1 outbound target (Phase 10): waterfall-enriched, AI-personalized,
    deliverability-guarded, and policy-gated before send."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    campaign_id: str = Field(index=True, foreign_key="campaign.id")
    name: str
    domain: str = ""
    company: str = ""
    title: str = ""
    signal: str = ""  # enrichment reason-to-reach-out
    personalized_line: str = ""
    status: str = "new"  # new | enriched | sent | blocked
    created_at: datetime = Field(default_factory=_now)


class ConsentRecord(SQLModel, table=True):
    """A consent receipt (OneTrust / IAB-TCF shape): a marketing subject's basis for a
    purpose, checked before any outbound activation. Composes with the PolicyGate as a
    pre-send gate."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    subject_id: str  # email / domain / prospect identifier
    purpose: str = "outbound_email"  # outbound_email | analytics | personalization
    status: str = "granted"  # granted | denied | withdrawn
    legal_basis: str = "consent"  # consent | legitimate_interest
    source: str = "manual"
    created_at: datetime = Field(default_factory=_now)


class PlannedAction(SQLModel, table=True):
    """Phase 14 — the autonomous orchestrator's proposed next action. The brain OBSERVES
    state across capabilities (flywheel / funnel / segments / market / reliability) and
    emits a ranked queue; the human Accepts or Ignores (Agent Inbox). Each ``type`` maps to
    an existing capability — the planner selects + sequences, it doesn't invent."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    type: str  # run_incrementality | draft_whitespace | import_history | validate_segment | review_autonomy
    title: str
    rationale: str
    priority: int = 50
    autonomy_level: str = "ai_draft_human_review"
    status: str = "proposed"  # proposed | accepted | ignored
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class EvalSuite(SQLModel, table=True):
    """Phase 12 — LLMOps: a named set of eval cases gating an agent/capability's quality."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    name: str
    created_at: datetime = Field(default_factory=_now)


class EvalCase(SQLModel, table=True):
    """One eval example: an input + the expectation a grader checks."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    suite_id: str = Field(index=True, foreign_key="evalsuite.id")
    name: str
    input_text: str
    expectation: str  # no_policy_block | geo_citable


class EvalRun(SQLModel, table=True):
    """A scored run of a suite — the regression-gate record (overall score + pass/fail)."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    suite_id: str = Field(index=True, foreign_key="evalsuite.id")
    overall: float = 0.0
    passed: bool = False
    n_cases: int = 0
    created_at: datetime = Field(default_factory=_now)


class StrategySession(SQLModel, table=True):
    """The persisted STATE of the strategy co-creation loop (circuit A) — loop engineering
    made concrete. Each `advance` is one verified turn; the draft + turn history accrue here
    so the loop is stateful (not a goldfish), reopenable, and feeds downstream. `status`
    flips to 'done' when the human says 'good enough, let's make content'."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.id")
    member_id: str = Field(foreign_key="member.id")
    goal: str = ""
    inputs: list = Field(default_factory=list, sa_column=Column(JSON))  # [{type, value}]
    draft: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # current StrategyDraft
    turns: list = Field(default_factory=list, sa_column=Column(JSON))  # [{feedback, draft}]
    status: str = "active"  # active | done
    campaign_id: Optional[str] = Field(default=None, foreign_key="campaign.id")  # A→B handoff target
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
