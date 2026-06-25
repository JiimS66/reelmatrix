"""The OutcomeLearner — the closing edge of the effect flywheel.

It rebuilds the per-attribute Beta posteriors (`AttributeOutcome`) from a tenant's
published posts + their metrics, and serves the "what's working" priors back into
agent context (the 4th, derived memory layer). This is what turns the system's
self-CORRECTION into outcome-LEARNING.

Mock-first: metrics come from a stored `MetricSnapshot` (real GA4 sync writes these)
or deterministic `mock_metrics` until a real source is connected. The rebuild is FULL
and IDEMPOTENT — calling it twice yields the same table.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlmodel import Session, select

from core.content.tracking import mock_metrics
from core.db.models import (
    AttributeOutcome,
    IncrementalityTest,
    MetricSnapshot,
    Post,
    Task,
    WinningPattern,
)
from core.growth.attributes import ATTRIBUTE_TYPES, extract_attributes

# Cold-start guard: below this many posts in a slice, look-ups fall back to a broader
# slice (channel×segment -> channel -> global) so we never advise from one data point.
_MIN_POSTS = 3

_TYPE_LABEL = {"hook_type": "hook", "cta_style": "CTA", "length_bucket": "length"}


def _post_metrics(session: Session, post: Post) -> tuple[int, int]:
    """(impressions, conversions) for a post — latest snapshot, else deterministic mock."""
    snap = session.exec(
        select(MetricSnapshot)
        .where(MetricSnapshot.post_id == post.id)
        .order_by(MetricSnapshot.captured_at.desc())  # type: ignore[attr-defined]
    ).first()
    if snap is not None:
        return snap.impressions, snap.signups
    m = mock_metrics(post.id)
    return m["impressions"], m["signups"]


def learn_outcomes(session: Session, tenant_id: str) -> int:
    """Full, idempotent rebuild of the tenant's AttributeOutcome posteriors from its
    published posts. Each post contributes to three slices per attribute —
    (channel, segment), (channel, ""), ("", "") — so look-ups can fall back. Returns the
    number of posterior rows written."""
    posts = list(session.exec(select(Post).where(Post.tenant_id == tenant_id)).all())
    # Causal de-bias (Phase 11): scale an attribute's wins by its measured lift multiplier
    # (default 1.0 → unchanged until an IncrementalityTest exists).
    multipliers = {
        t.attribute_value: t.multiplier
        for t in session.exec(
            select(IncrementalityTest).where(IncrementalityTest.tenant_id == tenant_id)
        ).all()
    }
    # (attr_type, attr_value, channel, segment) -> [impressions, conversions, n_posts]
    buckets: dict[tuple[str, str, str, str], list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    for post in posts:
        task = session.get(Task, post.asset_task_id)
        if task is None or not task.output:
            continue
        attrs = extract_attributes(task.output)
        if not attrs:
            continue
        impressions, conversions = _post_metrics(session, post)
        params = task.params or {}
        channel = str(params.get("channel") or "")
        segment = str(params.get("segment") or "")
        for atype, avalue in attrs.items():
            conv_eff = conversions * multipliers.get(avalue, 1.0)  # de-biased wins
            for ch, seg in {(channel, segment), (channel, ""), ("", "")}:
                bucket = buckets[(atype, avalue, ch, seg)]
                bucket[0] += impressions
                bucket[1] += conv_eff
                bucket[2] += 1

    # Replace the tenant's rows (idempotent rebuild).
    for row in session.exec(
        select(AttributeOutcome).where(AttributeOutcome.tenant_id == tenant_id)
    ).all():
        session.delete(row)
    now = datetime.now(timezone.utc)
    for (atype, avalue, ch, seg), (impressions, conversions, n) in buckets.items():
        session.add(
            AttributeOutcome(
                tenant_id=tenant_id,
                attribute_type=atype,
                attribute_value=avalue,
                channel=ch,
                segment=seg,
                impressions=int(impressions),
                conversions=int(round(conversions)),
                n_posts=int(n),
                alpha=1.0 + conversions,
                beta=1.0 + max(0.0, impressions - conversions),
                updated_at=now,
            )
        )
    session.commit()
    return len(buckets)


def _mean(row: AttributeOutcome) -> float:
    return row.alpha / (row.alpha + row.beta)


def _slice_rows(
    session: Session, tenant_id: str, channel: str, segment: str
) -> list[AttributeOutcome]:
    return list(
        session.exec(
            select(AttributeOutcome).where(
                AttributeOutcome.tenant_id == tenant_id,
                AttributeOutcome.channel == channel,
                AttributeOutcome.segment == segment,
            )
        ).all()
    )


def learned_priors(
    session: Session, tenant_id: str, channel: str = "", segment: str = ""
) -> list[str]:
    """The "what's working" memo injected into the copywriter/designer context — the
    derived (4th) memory layer. For each attribute type, name the best (and, if clearly
    worse, the worst) value in the most specific slice that has enough data, falling
    back (channel,segment) -> (channel,"") -> ("",""). Returns ≤5 short strings."""
    memos: list[str] = []
    for atype in ATTRIBUTE_TYPES:
        rows: list[AttributeOutcome] = []
        scope = "overall"
        for ch, seg in ((channel, segment), (channel, ""), ("", "")):
            candidate = [
                r
                for r in _slice_rows(session, tenant_id, ch, seg)
                if r.attribute_type == atype and r.n_posts >= _MIN_POSTS
            ]
            if candidate:
                rows = candidate
                scope = f"{ch} × {seg}" if (ch and seg) else (ch or "overall")
                break
        if not rows:
            continue
        rows.sort(key=_mean, reverse=True)
        best = rows[0]
        memos.append(
            f"On {scope}, '{best.attribute_value}' {_TYPE_LABEL[atype]} converts best "
            f"so far (CVR {_mean(best) * 100:.1f}%, n={best.n_posts})."
        )
        if len(rows) >= 2 and _mean(rows[-1]) < _mean(best) * 0.6:
            worst = rows[-1]
            memos.append(
                f"'{worst.attribute_value}' {_TYPE_LABEL[atype]} underperforms "
                f"(CVR {_mean(worst) * 100:.1f}%, n={worst.n_posts}) — consider avoiding."
            )
    memos = memos[:4] + _winning_pattern_memos(session, tenant_id, channel, segment)
    return memos[:6]


def _winning_pattern_memos(
    session: Session, tenant_id: str, channel: str = "", segment: str = ""
) -> list[str]:
    """Experiment-proven attribute combos (Phase 5b) promoted to generation rules,
    injected right next to the flywheel memo so proven winners actively steer drafts."""
    rows = [
        w
        for w in session.exec(
            select(WinningPattern).where(WinningPattern.tenant_id == tenant_id)
        ).all()
        if (not w.channel or w.channel == channel)
        and (not w.segment or w.segment == segment)
    ]
    rows.sort(key=lambda w: w.confidence, reverse=True)
    memos: list[str] = []
    for w in rows[:2]:
        attrs = ", ".join(f"{k}={v}" for k, v in (w.attributes or {}).items())
        memos.append(
            f"Experiment-proven: [{attrs}] lifted CVR +{w.lift * 100:.0f}% "
            f"(p={w.confidence:.2f}) — prefer it."
        )
    return memos


def attribute_insights(
    session: Session, tenant_id: str, channel: str = "", segment: str = ""
) -> list[dict]:
    """The learned scoreboard for a UI: every attribute value in a slice with its CVR
    and sample size, best-first within each type. Defaults to the global slice."""
    rows = _slice_rows(session, tenant_id, channel, segment)
    rows.sort(key=lambda r: (r.attribute_type, -_mean(r)))
    return [
        {
            "attribute_type": r.attribute_type,
            "attribute_value": r.attribute_value,
            "cvr": round(_mean(r) * 100, 2),
            "n_posts": r.n_posts,
            "impressions": r.impressions,
            "conversions": r.conversions,
        }
        for r in rows
    ]
