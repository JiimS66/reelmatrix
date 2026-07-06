"""Outbound review-queue notifications.

When work lands in a human's queue, POST a small JSON payload to the endpoint
the team configured (Slack/Feishu/DingTalk incoming webhook, or anything that
accepts JSON). Fire-and-forget by contract: a dead endpoint must never break —
or even slow down noticeably — the pipeline, so the timeout is short and every
error is swallowed. No-op when NOTIFY_WEBHOOK_URL is unset (the default).
"""

from typing import Optional

import httpx

from configs.settings import get_settings

_TIMEOUT_SECONDS = 3.0


def notify_review_needed(
    *,
    task_id: str,
    task_title: str,
    campaign_name: str,
    assignee_name: Optional[str] = None,
) -> None:
    url = (get_settings().notify_webhook_url or "").strip()
    if not url:
        return
    payload = {
        "source": "reelmatrix",
        "event": "needs_review",
        "task_id": task_id,
        "title": task_title,
        "campaign": campaign_name,
        "assignee": assignee_name,
        # Slack/Feishu-friendly plain line, so a bare incoming webhook renders sanely.
        "text": (
            f"ReelMatrix: \"{task_title}\" ({campaign_name}) is waiting on "
            f"{assignee_name or 'a human'} for review."
        ),
    }
    try:
        httpx.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
    except httpx.HTTPError:
        pass  # notifications are best-effort by design
