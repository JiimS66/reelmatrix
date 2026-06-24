"""Team workspace API: campaign board, member inbox, and task actions.

Auth is a development stub: the acting member is taken from the ``X-Member-Id``
header. Replace with real authentication before any non-local use.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from apps.api.schemas.team import (
    AssignRequest,
    AtomRead,
    BoardRead,
    CampaignRead,
    CommentRead,
    CommentRequest,
    CreateCampaignRequest,
    EditRequest,
    EventRead,
    MemberRead,
    MetricsRequest,
    MilestoneRead,
    PerformanceData,
    PerformanceRow,
    ReviewRequest,
    ScheduleRead,
    SubmitRequest,
    TaskDetailRead,
    TaskRead,
    TodoItem,
)
from apps.api.services import team_service
from core.db.engine import get_session
from core.db.models import Member
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
    campaign, rows, totals = team_service.campaign_performance(
        session, actor, campaign_id
    )
    return PerformanceData(
        campaign_id=campaign.id,
        rows=[PerformanceRow(**row) for row in rows],
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


@router.get("/todo", response_model=list[TodoItem])
def get_todo(
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[TodoItem]:
    return [
        TodoItem(campaign_name=name, task=TaskRead.model_validate(task))
        for name, task in team_service.get_todo(session, actor)
    ]


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
    )


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


@router.post("/tasks/{task_id}/metrics", response_model=PerformanceData)
def record_metrics(
    task_id: str,
    payload: MetricsRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> PerformanceData:
    snapshot = team_service.record_metrics(
        session,
        actor,
        task_id,
        impressions=payload.impressions,
        clicks=payload.clicks,
        signups=payload.signups,
    )
    return _performance_response(
        session, actor, snapshot.campaign_id, note="Manual metrics recorded."
    )
