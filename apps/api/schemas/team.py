from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from core.content.insight import predicted_performance
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
    locked: bool = False
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> Optional[dict]:
        """0–100 content score derived from the checks (None when not scoreable)."""
        return content_score(self.checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def predicted_performance(self) -> Optional[dict]:
        """0–100 predicted-performance heuristic for a post (None otherwise)."""
        if self.kind != TaskKind.ASSET:
            return None
        return predicted_performance(self.output, (self.params or {}).get("channel", ""))


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


class TermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    term: str
    term_type: str
    replacement: Optional[str]
    case_sensitive: bool
    note: str


class TermRequest(BaseModel):
    term: str
    term_type: str = "avoid"
    replacement: Optional[str] = None
    case_sensitive: bool = False
    note: str = ""


class BrandRead(BaseModel):
    voice: str = ""
    tone_rules: list[str] = []
    forbidden_words: list[str] = []
    approved_phrases: list[str] = []
    proof_points: list[dict] = []  # [{claim, source}]
    segments: list[dict] = []  # ICP: [{name, description, platforms, pain_points, reach_tactics}]


class SegmentRequest(BaseModel):
    name: str
    description: str = ""
    profile: str = ""  # firmographics: industry / size / role / region
    platforms: list[str] = []
    pain_points: list[str] = []
    value_props: list[str] = []
    objections: list[str] = []
    reach_tactics: list[str] = []


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


class TrendAngle(BaseModel):
    angle: str
    safe: bool
    score: int
    reason: str


class TrendDraftRequest(BaseModel):
    angle: str
    channel: str = "X / Twitter"


class TrendRefresh(BaseModel):
    campaign_id: str
    timely_angles: list[str]


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: int
    source: str
    created_by: Optional[str]
    created_at: datetime


class AnnotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    target: str
    anchor: dict
    body: str
    resolved: bool
    resolved_by: Optional[str]
    created_at: datetime


class AnnotationRequest(BaseModel):
    body: str
    target: str = "general"
    anchor: dict = {}


class ResolveRequest(BaseModel):
    resolved: bool = True


class LockRequest(BaseModel):
    locked: bool = True


class TaskDetailRead(BaseModel):
    task: TaskRead
    ai_draft: Optional[dict]
    comments: list[CommentRead]
    events: list[EventRead]
    available_actions: list[str]
    versions: list[VersionRead] = []
    annotations: list[AnnotationRead] = []


class DirectMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender: str
    kind: str
    title: Optional[str]
    task_id: Optional[str] = None
    body: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    body: str
    kind: str = "message"
    title: Optional[str] = None


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


class MemberProfileRead(BaseModel):
    member: OrgMemberRead
    fleet: Optional[FleetAgent]
    tasks: list[TaskRead]


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


class AttributeInsight(BaseModel):
    """One learned content-attribute posterior: its conversion rate + sample size."""

    attribute_type: str
    attribute_value: str
    cvr: float
    n_posts: int
    impressions: int
    conversions: int


class GrowthInsights(BaseModel):
    """The effect-flywheel made visible: the learned scoreboard + the 'what's working'
    priors the agents now generate from."""

    attributes: list[AttributeInsight]
    priors: list[str]


class IncrementalityRow(BaseModel):
    attribute_type: str
    attribute_value: str
    naive_conversions: int
    incremental_conversions: int
    multiplier: float
    lift_pct: float


class IncrementalityResult(BaseModel):
    tests: list[IncrementalityRow]
    insights: GrowthInsights


class PlannedActionRead(BaseModel):
    id: str
    type: str
    title: str
    rationale: str
    priority: int
    autonomy_level: str
    status: str


class ExperimentVariantRead(BaseModel):
    key: str
    attributes: dict
    rationale: str
    impressions: int
    conversions: int
    cvr: float
    chance_to_beat_control: float
    result_status: str


class ExperimentRead(BaseModel):
    id: str
    hypothesis: str
    channel: str
    segment: str
    status: str
    variants: list[ExperimentVariantRead]


class DesignExperimentRequest(BaseModel):
    hypothesis: str
    channel: str = ""
    segment: str = ""
    n: int = 3


class SegmentScore(BaseModel):
    segment: str
    score: int
    status: str
    n_posts: int
    cvr: float
    drivers: list[str]


class SegmentCandidate(BaseModel):
    id: str
    name: str
    rationale: str
    evidence: dict


class SegmentScorecard(BaseModel):
    segments: list[SegmentScore]
    candidates: list[SegmentCandidate]


class CompetitorCardRead(BaseModel):
    name: str
    positioning: str
    recent_change: str


class MarketIntelRead(BaseModel):
    competitors: list[CompetitorCardRead]
    audience_questions: list[str]
    share_of_voice: dict[str, float]
    whitespace: list[str]


class WhitespaceRequest(BaseModel):
    angle: str


class NarrativeRequest(BaseModel):
    value_proposition: str = ""
    messaging_pillars: list[dict] = []


class NarrativeRead(BaseModel):
    value_proposition: str
    messaging_pillars: list[dict]


class FunnelCoverage(BaseModel):
    stages: list[str]
    segments: list[str]
    matrix: dict
    gaps: list[dict]


class GapRequest(BaseModel):
    funnel_stage: str
    segment: str


class PillarRead(BaseModel):
    id: str
    title: str
    kind: str
    derivatives: int


class CreatePillarRequest(BaseModel):
    title: str
    kind: str = "doc"
    source_text: str = ""


class AtomizeRequest(BaseModel):
    channels: list[str] = []


class ClipRead(BaseModel):
    hook_sentence: str
    clip_score: int
    reason: str
    start: int
    end: int


class ClipsRead(BaseModel):
    pillar_id: str
    clips: list[ClipRead]


class ClipDraftRequest(BaseModel):
    hook_sentence: str


class ReliabilityRow(BaseModel):
    member_id: str
    display_name: str
    role: str
    runs: int
    reliability: int
    recommended_mode: str


class PolicyViolation(BaseModel):
    rule: str
    severity: str
    message: str
    fix: str


class PolicyVerdictRead(BaseModel):
    allow: bool
    violations: list[PolicyViolation]


class PaidVariant(BaseModel):
    angle: str
    headline: str
    creative_score: int
    predicted_ctr: float
    allocated_budget: float


class PaidPlan(BaseModel):
    total_budget: float
    variants: list[PaidVariant]


class ProspectRead(BaseModel):
    id: str
    name: str
    company: str
    title: str
    signal: str
    personalized_line: str
    status: str


class AddProspectRequest(BaseModel):
    name: str
    domain: str = ""


class ImportHistoricalRequest(BaseModel):
    rows: list[dict]


class ImportResult(BaseModel):
    imported: int
    insights: GrowthInsights


class BrandKnowledgeRequest(BaseModel):
    text: str


class BrandDraftRead(BaseModel):
    voice: str
    value_proposition: str
    messaging_pillars: list[dict]
    tone_rules: list[str]


class BrandKnowledgeResult(BaseModel):
    draft: BrandDraftRead
    applied: bool


class DeploymentStatus(BaseModel):
    profile: str
    providers: dict
    gates: dict
    data_leaves_environment: bool


class ConsentRequest(BaseModel):
    subject_id: str
    purpose: str = "outbound_email"
    status: str = "granted"
    legal_basis: str = "consent"
