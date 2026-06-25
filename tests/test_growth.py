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


def test_design_variants_are_self_consistent() -> None:
    from core.growth.experiments import design_variants

    variants = design_variants("verifying AI code", n=4)
    assert len(variants) == 4
    assert variants[0]["key"] == "control"
    # Each variant's drafted content round-trips to its tagged attributes — so the
    # experiment's labels match what the flywheel would read off the content.
    for v in variants:
        got = extract_attributes(v["content"])
        assert got["hook_type"] == v["attributes"]["hook_type"]
        assert got["cta_style"] == v["attributes"]["cta_style"]
        assert got["length_bucket"] == v["attributes"]["length_bucket"]


def test_bayesian_stats_detects_a_clear_winner() -> None:
    from types import SimpleNamespace

    from core.growth.stats import create_stats_provider

    stats = create_stats_provider()
    control = SimpleNamespace(impressions=2000, conversions=60)  # 3%
    variant = SimpleNamespace(impressions=2000, conversions=180)  # 9%
    assert stats.chance_to_beat_control(control, variant) > 0.95
    assert stats.chance_to_beat_control(variant, control) < 0.05


def test_measure_lift_yields_debias_multiplier() -> None:
    from core.growth.incrementality import measure_lift

    over = measure_lift("bold_claim", 100)
    assert over["multiplier"] < 1.0 and over["incremental_conversions"] == 55
    assert measure_lift("curiosity", 100)["multiplier"] > 1.0
    assert measure_lift("unknown_attr", 100)["multiplier"] == 1.0  # neutral default


def test_flywheel_debiases_with_incrementality() -> None:
    from core.db.models import IncrementalityTest

    session = _session()
    for i in range(3):
        _add_post(session, i, title="The only way to ship AI", signups=80)  # bold_claim
    learn_outcomes(session, TENANT)

    def _bold(s):
        return next(
            r for r in s.exec(select(AttributeOutcome)).all()
            if r.attribute_type == "hook_type" and r.attribute_value == "bold_claim"
            and r.channel == "" and r.segment == ""
        )

    naive_conv = _bold(session).conversions
    session.add(IncrementalityTest(
        tenant_id=TENANT, attribute_type="hook_type",
        attribute_value="bold_claim", multiplier=0.5,
    ))
    session.commit()
    learn_outcomes(session, TENANT)
    assert _bold(session).conversions < naive_conv  # de-biased shrinks the over-claimer


def test_geo_issues_flag_citability_gaps() -> None:
    from core.content.geo import geo_issues

    bare = {i["rule"] for i in geo_issues("We help teams ship faster")}
    assert {"add_statistic", "cite_source", "faq_structure"} <= bare
    rich = {
        i["rule"]
        for i in geo_issues("Slow shipping? 80% of teams improve, according to our study.")
    }
    assert not ({"add_statistic", "cite_source", "faq_structure"} & rich)


def test_budget_optimizer_allocates_by_marginal_roi() -> None:
    from core.paid.optimizer import ChannelCurve, optimize_budget

    plan = optimize_budget(
        [ChannelCurve("A", 8000, 2000), ChannelCurve("B", 4000, 1500)], 4000, step=100
    )
    assert abs(sum(r["allocated"] for r in plan["allocation"]) - 4000) < 100
    assert all("marginal_roi" in r for r in plan["allocation"])


def test_identity_resolution_stitches_shared_ids() -> None:
    from core.identity.resolver import resolve_identities

    records = [
        {"anon_id": "a1", "email": "dana@acme.dev"},
        {"email": "dana@acme.dev", "user_id": "u1", "company": "Acme"},
        {"anon_id": "a2", "email": "sam@acme.dev"},
    ]
    profiles = resolve_identities(records)
    assert len(profiles) == 2  # dana (stitched via email) + sam
    dana = next(p for p in profiles if p["record_count"] == 2)
    assert dana["main_id"].startswith("user_id:")  # priority main_id
    assert dana["traits"].get("company") == "Acme"
    # blocked/empty values don't runaway-merge.
    assert len(resolve_identities([{"email": "", "anon_id": "x"}, {"email": "", "anon_id": "y"}])) == 2


def test_eval_grader_uses_real_gates() -> None:
    from core.evals.grader import grade_case

    assert grade_case("We help teams ship code.", "no_policy_block")["passed"] is True
    assert grade_case(
        "We are the best #1 tool, guaranteed results.", "no_policy_block"
    )["passed"] is False
    assert grade_case(
        "Slow? 80% improve, according to our study.", "geo_citable"
    )["score"] >= 0.5
