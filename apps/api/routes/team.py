"""Team workspace API: campaign board, member inbox, and task actions.

Auth is a development stub: the acting member is taken from the ``X-Member-Id``
header. Replace with real authentication before any non-local use.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from apps.api.schemas.team import (
    AgentRoleRead,
    AnnotationRead,
    AnnotationRequest,
    AssignRequest,
    AtomRead,
    BoardRead,
    BrandRead,
    CampaignRead,
    CommentRead,
    CommentRequest,
    CreateCampaignRequest,
    CreateOrgMemberRequest,
    DirectMessageRead,
    EditRequest,
    EventRead,
    FleetAgent,
    LockRequest,
    MemberProfileRead,
    MemberRead,
    MetricsRequest,
    MilestoneRead,
    OrgMemberRead,
    OrgRead,
    PerformanceData,
    PlatformPerformance,
    ResolveRequest,
    ReviewRequest,
    ScheduleRead,
    SegmentRequest,
    SendMessageRequest,
    SubmitRequest,
    TaskDetailRead,
    TaskRead,
    TermRead,
    TermRequest,
    GrowthInsights,
    TodoItem,
    TrendAngle,
    TrendDraftRequest,
    TrendRefresh,
    UpdateOrgMemberRequest,
    VersionRead,
)
from apps.api.services import team_service
from core.agents.roles import ROLES
from core.analytics.sync import sync_campaign_analytics
from core.growth.learner import learn_outcomes
from core.db.engine import get_session
from core.db.models import Member, TaskKind
from core.publish.publish import publish_campaign_posts
from core.trends.refresh import refresh_campaign_trends
from core.workflows.task_runner import TaskRunner

router = APIRouter(prefix="/api/v1/team", tags=["team"])


def get_current_member(
    x_member_id: str = Header(..., alias="X-Member-Id"),
    session: Session = Depends(get_session),
) -> Member:
    member = session.get(Member, x_member_id)
    if member is None:
        raise HTTPException(status_code=401, detail="Unknown member.")
    return member


def _board_response(session: Session, actor: Member, campaign_id: str) -> BoardRead:
    campaign, tasks, members = team_service.get_board(session, actor, campaign_id)
    return BoardRead(
        campaign=CampaignRead.model_validate(campaign),
        tasks=[TaskRead.model_validate(task) for task in tasks],
        members=[MemberRead.model_validate(member) for member in members],
    )


@router.post("/campaigns", response_model=BoardRead)
def create_campaign(
    payload: CreateCampaignRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BoardRead:
    campaign = team_service.create_campaign(
        session,
        actor,
        name=payload.name,
        brief=payload.brief,
        template=payload.template,
        event_name=payload.event_name,
        event_date=payload.event_date,
        review_assets=payload.review_assets,
        with_visuals=payload.with_visuals,
    )
    return _board_response(session, actor, campaign.id)


@router.get("/campaigns", response_model=list[CampaignRead])
def list_campaigns(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[CampaignRead]:
    return [
        CampaignRead.model_validate(c)
        for c in team_service.list_campaigns(session, actor)
    ]


@router.get("/campaigns/{campaign_id}/board", response_model=BoardRead)
def get_board(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BoardRead:
    return _board_response(session, actor, campaign_id)


@router.post("/campaigns/{campaign_id}/run", response_model=BoardRead)
async def run_campaign(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BoardRead:
    team_service.get_board(session, actor, campaign_id)  # access check
    await TaskRunner(session).run_ready_tasks(campaign_id)
    return _board_response(session, actor, campaign_id)


@router.get("/members", response_model=list[MemberRead])
def list_members(
    session: Session = Depends(get_session),
) -> list[MemberRead]:
    # Dev bootstrap (no auth): lets the stub UI pick who to act as.
    return [MemberRead.model_validate(m) for m in team_service.list_all_members(session)]


@router.get("/fleet", response_model=list[FleetAgent])
def get_fleet(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[FleetAgent]:
    return [FleetAgent(**row) for row in team_service.agent_fleet(session, actor)]


@router.get("/org", response_model=OrgRead)
def get_org(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> OrgRead:
    members = team_service.get_org(session, actor)
    return OrgRead(
        members=[OrgMemberRead.from_member(m) for m in members],
        task_kinds=[kind.value for kind in TaskKind],
        agent_roles=[
            AgentRoleRead(key=r.key, title=r.title, job_description=r.job_description)
            for r in ROLES.values()
        ],
    )


@router.post("/org/members", response_model=OrgMemberRead)
def create_org_member(
    payload: CreateOrgMemberRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> OrgMemberRead:
    member = team_service.create_org_member(
        session,
        actor,
        display_name=payload.display_name,
        role=payload.role,
        job_description=payload.job_description,
        handles_kinds=payload.handles_kinds,
        provider=payload.provider,
        model=payload.model,
        reports_to=payload.reports_to,
    )
    return OrgMemberRead.from_member(member)


@router.post("/org/members/{member_id}", response_model=OrgMemberRead)
def update_org_member(
    member_id: str,
    payload: UpdateOrgMemberRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> OrgMemberRead:
    member = team_service.update_org_member(
        session,
        actor,
        member_id,
        job_description=payload.job_description,
        handles_kinds=payload.handles_kinds,
        reports_to=payload.reports_to,
        role=payload.role,
        provider=payload.provider,
        model=payload.model,
    )
    return OrgMemberRead.from_member(member)


@router.get("/members/{member_id}/profile", response_model=MemberProfileRead)
def get_member_profile(
    member_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> MemberProfileRead:
    member, stat, tasks = team_service.member_profile(session, actor, member_id)
    return MemberProfileRead(
        member=OrgMemberRead.from_member(member),
        fleet=FleetAgent(**stat) if stat else None,
        tasks=[TaskRead.model_validate(t) for t in tasks],
    )


@router.get("/members/{member_id}/messages", response_model=list[DirectMessageRead])
def get_member_messages(
    member_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[DirectMessageRead]:
    return [
        DirectMessageRead.model_validate(m)
        for m in team_service.list_member_messages(session, actor, member_id)
    ]


@router.post("/members/{member_id}/messages", response_model=list[DirectMessageRead])
async def send_member_message(
    member_id: str,
    payload: SendMessageRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[DirectMessageRead]:
    messages = await team_service.send_member_message(
        session, actor, member_id,
        body=payload.body, kind=payload.kind, title=payload.title,
    )
    return [DirectMessageRead.model_validate(m) for m in messages]


@router.get("/inbox", response_model=list[TaskRead])
def get_inbox(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TaskRead]:
    return [TaskRead.model_validate(task) for task in team_service.get_inbox(session, actor)]


@router.get("/campaigns/{campaign_id}/schedule", response_model=ScheduleRead)
def get_schedule(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> ScheduleRead:
    campaign, milestones, tasks, angles = team_service.get_schedule(
        session, actor, campaign_id
    )
    return ScheduleRead(
        campaign=CampaignRead.model_validate(campaign),
        milestones=[MilestoneRead.model_validate(m) for m in milestones],
        tasks=[TaskRead.model_validate(t) for t in tasks],
        timely_angles=angles,
    )


def _performance_response(
    session: Session, actor: Member, campaign_id: str, *, note: str
) -> PerformanceData:
    campaign, platforms, totals = team_service.campaign_performance(
        session, actor, campaign_id
    )
    return PerformanceData(
        campaign_id=campaign.id,
        platforms=[PlatformPerformance(**p) for p in platforms],
        totals=totals,
        note=note,
    )


@router.get("/campaigns/{campaign_id}/performance", response_model=PerformanceData)
def get_performance(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> PerformanceData:
    return _performance_response(
        session,
        actor,
        campaign_id,
        note=(
            "Mock data. Connect owned-destination analytics + signup attribution "
            "(UTMs) for real conversions; platform APIs where available."
        ),
    )


@router.post("/campaigns/{campaign_id}/publish", response_model=PerformanceData)
async def publish_campaign(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> PerformanceData:
    campaign = team_service.get_campaign_for_lead(session, actor, campaign_id)
    live = await publish_campaign_posts(session, campaign)
    return _performance_response(
        session,
        actor,
        campaign_id,
        note=(
            f"Published {live} posts via the mock provider (deterministic permalinks). "
            "Swap PUBLISH_PROVIDER=buffer (or a native API) to ship for real."
        ),
    )


@router.post("/campaigns/{campaign_id}/analytics/sync", response_model=PerformanceData)
async def sync_analytics(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> PerformanceData:
    campaign = team_service.get_campaign_for_lead(session, actor, campaign_id)
    updated = await sync_campaign_analytics(session, campaign)
    learn_outcomes(session, campaign.tenant_id)  # GA4 回流后即刷新学习先验
    return _performance_response(
        session,
        actor,
        campaign_id,
        note=(
            f"Synced {updated} posts from GA4 (mock connector) by UTM. "
            "Swap ANALYTICS_SOURCE=ga4 with a service account for live conversions."
        ),
    )


@router.post("/campaigns/{campaign_id}/trends", response_model=TrendRefresh)
async def refresh_trends(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TrendRefresh:
    campaign = team_service.get_campaign_for_lead(session, actor, campaign_id)
    angles = await refresh_campaign_trends(session, campaign)
    return TrendRefresh(campaign_id=campaign.id, timely_angles=angles)


@router.get("/campaigns/{campaign_id}/trends", response_model=list[TrendAngle])
def scored_trends(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TrendAngle]:
    return [TrendAngle(**a) for a in team_service.score_angles(session, actor, campaign_id)]


@router.post("/campaigns/{campaign_id}/trends/draft", response_model=BoardRead)
async def draft_from_trend(
    campaign_id: str,
    payload: TrendDraftRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BoardRead:
    team_service.create_trend_draft(
        session, actor, campaign_id, angle=payload.angle, channel=payload.channel
    )
    await TaskRunner(session).run_ready_tasks(campaign_id)
    return _board_response(session, actor, campaign_id)


@router.get("/todo", response_model=list[TodoItem])
def get_todo(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TodoItem]:
    return [
        TodoItem(campaign_name=name, task=TaskRead.model_validate(task))
        for name, task in team_service.get_todo(session, actor)
    ]


@router.get("/review-queue", response_model=list[TodoItem])
def get_review_queue(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TodoItem]:
    """The cross-campaign 'needs your call' queue, each row tagged with its campaign."""
    return [
        TodoItem(campaign_name=name, task=TaskRead.model_validate(task))
        for name, task in team_service.get_review_queue(session, actor)
    ]


@router.get("/insights", response_model=GrowthInsights)
def read_growth_insights(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> GrowthInsights:
    """The learned 'what's working' scoreboard + priors (the effect flywheel)."""
    return GrowthInsights(**team_service.get_growth_insights(session, actor))


@router.post("/insights/learn", response_model=GrowthInsights)
def learn_growth_insights(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> GrowthInsights:
    """Rebuild the attribute posteriors from current post outcomes, then return them."""
    return GrowthInsights(**team_service.relearn_outcomes(session, actor))


@router.get("/brand", response_model=BrandRead)
def get_brand(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BrandRead:
    return _brand_read(team_service.get_brand(session, actor))


def _brand_read(brand) -> BrandRead:
    if brand is None:
        return BrandRead()
    return BrandRead(
        voice=brand.voice,
        tone_rules=brand.tone_rules,
        forbidden_words=brand.forbidden_words,
        approved_phrases=brand.approved_phrases,
        proof_points=brand.proof_points,
        segments=brand.segments,
    )


@router.post("/brand/segments", response_model=BrandRead)
def upsert_segment(
    payload: SegmentRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BrandRead:
    brand = team_service.upsert_segment(
        session, actor,
        name=payload.name, description=payload.description, profile=payload.profile,
        platforms=payload.platforms, pain_points=payload.pain_points,
        value_props=payload.value_props, objections=payload.objections,
        reach_tactics=payload.reach_tactics,
    )
    return _brand_read(brand)


@router.delete("/brand/segments/{name}", response_model=BrandRead)
def delete_segment(
    name: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BrandRead:
    return _brand_read(team_service.delete_segment(session, actor, name))


@router.get("/terms", response_model=list[TermRead])
def list_terms(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TermRead]:
    return [TermRead.model_validate(t) for t in team_service.list_terms(session, actor)]


@router.post("/terms", response_model=list[TermRead])
def create_term(
    payload: TermRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TermRead]:
    team_service.create_term(
        session, actor,
        term=payload.term, term_type=payload.term_type, replacement=payload.replacement,
        case_sensitive=payload.case_sensitive, note=payload.note,
    )
    return [TermRead.model_validate(t) for t in team_service.list_terms(session, actor)]


@router.delete("/terms/{term_id}", response_model=list[TermRead])
def delete_term(
    term_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TermRead]:
    team_service.delete_term(session, actor, term_id)
    return [TermRead.model_validate(t) for t in team_service.list_terms(session, actor)]


@router.get("/atoms", response_model=list[AtomRead])
def list_atoms(
    kind: Optional[str] = None,
    tag: Optional[str] = None,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[AtomRead]:
    atoms = team_service.list_atoms(session, actor, kind=kind, tag=tag)
    return [AtomRead.model_validate(atom) for atom in atoms]


@router.get("/tasks/{task_id}", response_model=TaskDetailRead)
def get_task(
    task_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskDetailRead:
    task, comments, events = team_service.get_task_detail(session, actor, task_id)
    return TaskDetailRead(
        task=TaskRead.model_validate(task),
        ai_draft=task.ai_draft,
        comments=[CommentRead.model_validate(c) for c in comments],
        events=[EventRead.model_validate(e) for e in events],
        available_actions=team_service.available_actions(actor, task),
        versions=[
            VersionRead.model_validate(v)
            for v in team_service.list_versions(session, actor, task_id)
        ],
        annotations=[
            AnnotationRead.model_validate(a)
            for a in team_service.list_annotations(session, actor, task_id)
        ],
    )


@router.post("/tasks/{task_id}/sync-visual", response_model=TaskRead)
async def sync_visual(
    task_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskRead:
    task = team_service.guard_post_edit(session, actor, task_id)
    await TaskRunner(session).sync_visual(task)
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/improve", response_model=TaskRead)
async def improve_task(
    task_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskRead:
    task = team_service.guard_post_edit(session, actor, task_id)
    await TaskRunner(session).improve(task)
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/lock", response_model=TaskRead)
def lock_task(
    task_id: str,
    payload: LockRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskRead:
    task = team_service.lock_task(session, actor, task_id, locked=payload.locked)
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/annotations", response_model=AnnotationRead)
def add_annotation(
    task_id: str,
    payload: AnnotationRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> AnnotationRead:
    row = team_service.create_annotation(
        session, actor, task_id,
        body=payload.body, target=payload.target, anchor=payload.anchor,
    )
    return AnnotationRead.model_validate(row)


@router.post("/annotations/{annotation_id}/resolve", response_model=AnnotationRead)
def resolve_annotation(
    annotation_id: str,
    payload: ResolveRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> AnnotationRead:
    row = team_service.resolve_annotation(
        session, actor, annotation_id, resolved=payload.resolved
    )
    return AnnotationRead.model_validate(row)


@router.post("/tasks/{task_id}/edit", response_model=TaskRead)
def edit_task(
    task_id: str,
    payload: EditRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskRead:
    task = team_service.edit_task(session, actor, task_id, output=payload.output)
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/assign", response_model=TaskRead)
def assign_task(
    task_id: str,
    payload: AssignRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskRead:
    task = team_service.assign_task(
        session, actor, task_id,
        member_id=payload.member_id, execution_mode=payload.execution_mode,
    )
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/submit", response_model=TaskRead)
def submit_task(
    task_id: str,
    payload: SubmitRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> TaskRead:
    task = team_service.submit_task(session, actor, task_id, output=payload.output)
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/review", response_model=BoardRead)
async def review_task(
    task_id: str,
    payload: ReviewRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> BoardRead:
    task = team_service.review_task(
        session, actor, task_id,
        action=payload.action, output=payload.output, note=payload.note,
    )
    if payload.action == "approve":
        await TaskRunner(session).run_ready_tasks(task.campaign_id)
    return _board_response(session, actor, task.campaign_id)


@router.post("/tasks/{task_id}/comments", response_model=CommentRead)
def add_comment(
    task_id: str,
    payload: CommentRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> CommentRead:
    comment = team_service.add_comment(session, actor, task_id, body=payload.body)
    return CommentRead.model_validate(comment)


@router.post("/posts/{post_id}/metrics", response_model=PerformanceData)
def record_metrics(
    post_id: str,
    payload: MetricsRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> PerformanceData:
    snapshot = team_service.record_metrics(
        session,
        actor,
        post_id,
        impressions=payload.impressions,
        clicks=payload.clicks,
        signups=payload.signups,
    )
    return _performance_response(
        session, actor, snapshot.campaign_id, note="Manual metrics recorded."
    )
