"""Phase 6 — ICP from assumption to validated result, + discovery.

`score_segments` turns each hand-entered segment into a 0–100 conversion score + a
status (validated / on-track / underperforming / unproven) + the attribute drivers that
work for it — a transparent weighted formula (Clay/Keyplay-style) over the SAME published
outcomes the flywheel reads, so a segment stops being a guess. `discover_segments`
surfaces a high-converting sub-cluster not yet defined as its own segment (mock standing
in for HDBSCAN over behavioral features). Both swap to real models behind these functions.
"""

from __future__ import annotations

from sqlmodel import Session, select

from core.content.tracking import mock_metrics
from core.db.models import MetricSnapshot, Post, Task
from core.growth.attributes import extract_attributes

_MIN_POSTS = 3  # below this a segment is "unproven" (cold-start)


def _post_outcome(session: Session, post: Post) -> tuple[int, int]:
    snap = session.exec(
        select(MetricSnapshot)
        .where(MetricSnapshot.post_id == post.id)
        .order_by(MetricSnapshot.captured_at.desc())  # type: ignore[attr-defined]
    ).first()
    if snap is not None:
        return snap.impressions, snap.signups
    m = mock_metrics(post.id)
    return m["impressions"], m["signups"]


def _aggregate(session: Session, tenant_id: str):
    """segment -> [impressions, conversions, n_posts, {attr=value: [imp, conv]}]."""
    agg: dict[str, list] = {}
    overall = [0, 0, 0]
    for post in session.exec(select(Post).where(Post.tenant_id == tenant_id)).all():
        task = session.get(Task, post.asset_task_id)
        if task is None:
            continue
        seg = (task.params or {}).get("segment", "") or "(untargeted)"
        imp, conv = _post_outcome(session, post)
        bucket = agg.setdefault(seg, [0, 0, 0, {}])
        bucket[0] += imp
        bucket[1] += conv
        bucket[2] += 1
        for atype, aval in extract_attributes(task.output).items():
            av = bucket[3].setdefault(f"{atype}={aval}", [0, 0])
            av[0] += imp
            av[1] += conv
        overall[0] += imp
        overall[1] += conv
        overall[2] += 1
    return agg, overall


def _top_drivers(attr_map: dict) -> list[str]:
    scored = [(k, c / i) for k, (i, c) in attr_map.items() if i > 0]
    scored.sort(key=lambda x: -x[1])
    return [k for k, _ in scored[:2]]


def score_segments(
    session: Session, tenant_id: str, segment_names: list[str]
) -> list[dict]:
    """A scorecard for every defined segment (plus any data-only bucket): 0–100 score vs
    the tenant baseline, a status, sample size, CVR, and the attribute drivers."""
    agg, overall = _aggregate(session, tenant_id)
    base_cvr = (overall[1] / overall[0]) if overall[0] else 0.0
    names = list(dict.fromkeys(list(segment_names) + list(agg.keys())))
    results = []
    for name in names:
        bucket = agg.get(name)
        if not bucket or bucket[2] == 0:
            results.append({
                "segment": name, "score": 0, "status": "unproven",
                "n_posts": 0, "cvr": 0.0, "drivers": [],
            })
            continue
        cvr = (bucket[1] / bucket[0]) if bucket[0] else 0.0
        n = bucket[2]
        ratio = (cvr / base_cvr) if base_cvr else 1.0
        score = max(0, min(100, round(50 * ratio)))  # baseline segment scores ~50
        if n < _MIN_POSTS:
            status = "unproven"
        elif ratio >= 1.15:
            status = "validated"
        elif ratio <= 0.85:
            status = "underperforming"
        else:
            status = "on-track"
        results.append({
            "segment": name, "score": score, "status": status, "n_posts": n,
            "cvr": round(cvr * 100, 2), "drivers": _top_drivers(bucket[3]),
        })
    results.sort(key=lambda r: -r["score"])
    return results


def discover_segments(
    session: Session, tenant_id: str, existing_names: list[str]
) -> list[dict]:
    """Surface a high-converting sub-cluster of a validated segment, defined by the
    attribute it responds to, as a candidate to target directly. Mock heuristic standing
    in for clustering — but grounded in real outcome data."""
    scorecard = score_segments(session, tenant_id, [])
    candidates = []
    for s in scorecard:
        if s["status"] != "validated" or not s["drivers"]:
            continue
        driver = s["drivers"][0]  # e.g. "hook_type=question"
        value = driver.split("=")[-1]
        name = f"{s['segment']} · responds to {value}"
        if name in existing_names:
            continue
        candidates.append({
            "name": name,
            "rationale": (
                f"A high-converting sub-cluster of '{s['segment']}' (CVR {s['cvr']}%) "
                f"that responds to {driver}. Promote it to target this group directly."
            ),
            "evidence": {"parent": s["segment"], "driver": driver, "cvr": s["cvr"]},
        })
        if len(candidates) >= 2:
            break
    return candidates
