"""Channel continuity: recall what already ran on a platform, and flag repeats.

The copywriter reads ``channel_history`` (the last few published posts on the
same platform) so the next post continues the thread instead of restarting it;
the ``continuity`` check flags a draft that overlaps too heavily with a recent
post on the same channel — the "don't repeat last week's hook" guardrail.
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.models import Post, Task

# Titles sharing at least this much word overlap with a recent same-channel post
# are flagged. Word-level Jaccard is crude but deterministic and offline.
_OVERLAP_THRESHOLD = 0.6

_STOPWORDS = {
    "a", "an", "and", "for", "from", "how", "in", "is", "it", "of", "on",
    "or", "our", "the", "this", "to", "with", "your", "you", "we",
}


def _words(text: str) -> set[str]:
    return {
        word
        for word in "".join(
            ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in text or ""
        ).split()
        if word not in _STOPWORDS and len(word) > 2
    }


def _overlap(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def channel_history(
    session: Session,
    *,
    tenant_id: str,
    platform: str,
    exclude_task_id: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    """The last ``limit`` published posts on this platform (newest first), as
    compact summaries the copywriter can read: title + date + opening line."""
    if not (platform or "").strip():
        return []
    posts = session.exec(
        select(Post)
        .where(Post.tenant_id == tenant_id, Post.platform == platform)
        .order_by(Post.published_at.desc(), Post.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    history: list[dict] = []
    for post in posts:
        if exclude_task_id is not None and post.asset_task_id == exclude_task_id:
            continue
        task = session.get(Task, post.asset_task_id)
        output = (task.output if task is not None else None) or {}
        content = str(output.get("content", ""))
        history.append(
            {
                "title": str(output.get("title", "")),
                "published_at": post.published_at,
                "opening": content.split("\n", 1)[0][:160],
            }
        )
        if len(history) >= limit:
            break
    return history


def channel_exemplars(
    session: Session,
    *,
    tenant_id: str,
    platform: str,
    exclude_task_id: Optional[str] = None,
    limit: int = 2,
) -> list[dict]:
    """The channel's proven winners, as few-shot exemplars for the copywriter.

    For an open-weight model, two real high-performing posts from the same
    channel beat any amount of prompt instruction. Ranked by the latest
    signup count (real snapshot when present, deterministic mock otherwise —
    same rule as the performance view)."""
    from core.content.tracking import mock_metrics
    from core.db.models import MetricSnapshot

    if not (platform or "").strip():
        return []
    posts = session.exec(
        select(Post).where(Post.tenant_id == tenant_id, Post.platform == platform)
    ).all()
    ranked: list[tuple[int, dict]] = []
    for post in posts:
        if exclude_task_id is not None and post.asset_task_id == exclude_task_id:
            continue
        task = session.get(Task, post.asset_task_id)
        output = (task.output if task is not None else None) or {}
        content = str(output.get("content", ""))
        if not content.strip():
            continue
        snapshot = session.exec(
            select(MetricSnapshot)
            .where(MetricSnapshot.post_id == post.id)
            .order_by(MetricSnapshot.captured_at.desc())  # type: ignore[attr-defined]
        ).first()
        signups = snapshot.signups if snapshot is not None else mock_metrics(post.id)["signups"]
        ranked.append(
            (
                signups,
                {
                    "title": str(output.get("title", "")),
                    "content": content[:800],
                    "call_to_action": str(output.get("call_to_action", "")),
                    "signups": signups,
                },
            )
        )
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [exemplar for _, exemplar in ranked[:limit]]


def continuity_issues(asset: dict, history: list[dict]) -> list[dict]:
    """Flag a draft whose title/hook rehashes a recent post on the same channel."""
    issues: list[dict] = []
    title = str((asset or {}).get("title", ""))
    opening = str((asset or {}).get("content", "")).split("\n", 1)[0]
    for prior in history or []:
        for label, current, previous in (
            ("title", title, prior.get("title", "")),
            ("opening", opening, prior.get("opening", "")),
        ):
            score = _overlap(current, previous)
            if score >= _OVERLAP_THRESHOLD:
                issues.append(
                    {
                        "code": "repeats_recent_post",
                        "detail": (
                            f"The {label} overlaps {int(score * 100)}% with the "
                            f"{prior.get('published_at', 'recent')} post "
                            f"\"{prior.get('title', '')[:60]}\" on this channel — "
                            "vary the hook or continue the thread explicitly."
                        ),
                    }
                )
                break  # one flag per prior post is enough
    return issues
