"""Phase 5a — the effect flywheel: attribute extraction + OutcomeLearner posteriors +
learned priors. These exercise the loop's correctness on controlled data (the mock
content can't guarantee attribute spread, so we construct it)."""

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from core.db.engine import init_db
from core.db.models import AttributeOutcome, MetricSnapshot, Post, Task, TaskKind
from core.growth.attributes import extract_attributes
from core.growth.learner import attribute_insights, learn_outcomes, learned_priors

TENANT = "t1"
_CONTENT = " ".join(["word"] * 50)  # a fixed medium-length body so length is constant


def _session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    init_db(engine)
    return Session(engine)


def _add_post(session, i, *, title, signups, channel="LinkedIn", segment="Eng"):
    task = Task(
        tenant_id=TENANT, campaign_id="c1", kind=TaskKind.ASSET, title=f"t{i}",
        output={"title": title, "content": _CONTENT, "call_to_action": "Sign up today"},
        params={"channel": channel, "segment": segment},
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    post = Post(
        tenant_id=TENANT, campaign_id="c1", asset_task_id=task.id, platform=channel,
        url="https://x", published_at="2026-01-01",
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    session.add(MetricSnapshot(
        tenant_id=TENANT, campaign_id="c1", post_id=post.id, source="test",
        impressions=1000, clicks=signups * 5, signups=signups,
    ))
    session.commit()


def test_extract_attributes_reads_hook_cta_length() -> None:
    attrs = extract_attributes(
        {"title": "Are you shipping AI code blind?", "content": "short body",
         "call_to_action": "Sign up today"}
    )
    assert attrs["hook_type"] == "question"
    assert attrs["cta_style"] == "direct"
    assert attrs["length_bucket"] == "short"


def test_learner_builds_posteriors_and_ranks_winners() -> None:
    session = _session()
    # 3 high-converting "question" posts vs 3 low-converting "statement" posts.
    for i in range(3):
        _add_post(session, i, title="Are you shipping AI code blind?", signups=80)
    for i in range(3, 6):
        _add_post(session, i, title="Verify your AI code", signups=10)

    rows = learn_outcomes(session, TENANT)
    assert rows > 0

    # The global slice scoreboard ranks the question hook above the statement hook.
    insights = attribute_insights(session, TENANT)
    hooks = [a for a in insights if a["attribute_type"] == "hook_type"]
    assert hooks[0]["attribute_value"] == "question"  # best-first
    assert hooks[0]["cvr"] > hooks[-1]["cvr"]
    by_value = {h["attribute_value"]: h for h in hooks}
    assert by_value["question"]["n_posts"] == 3

    # The injected memo names the winner (and flags the clear loser).
    priors = learned_priors(session, TENANT)
    assert any("question" in p and "converts best" in p for p in priors)
    assert any("statement" in p and "underperforms" in p for p in priors)


def test_learn_is_idempotent() -> None:
    session = _session()
    for i in range(4):
        _add_post(session, i, title="Are you shipping AI code blind?", signups=50)
    learn_outcomes(session, TENANT)
    first = len(session.exec(select(AttributeOutcome)).all())
    learn_outcomes(session, TENANT)
    second = len(session.exec(select(AttributeOutcome)).all())
    assert first == second and first > 0


def test_cold_start_suppresses_thin_advice() -> None:
    session = _session()
    # Only 1 post — below the _MIN_POSTS cold-start threshold → no priors yet.
    _add_post(session, 0, title="Are you shipping AI code blind?", signups=80)
    learn_outcomes(session, TENANT)
    assert learned_priors(session, TENANT) == []
