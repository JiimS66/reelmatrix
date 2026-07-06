"""Pump the local demo into a full-feature state — every tab alive, nothing embarrassing.

Run AFTER seeding, against a running API:

    DATABASE_URL=... LLM_PROVIDER=mock uv run python -m core.db.seed
    uv run uvicorn apps.api.main:app --port 8000 &
    uv run python scripts/demo_prep.py

What it does (as the lead, via the public API — the same clicks a user would make):
  1. creates + runs the TestSprite launch campaign (review-gated, with visuals)
  2. approves all but TWO review items (left pending so the Home queue has real work)
  3. publishes approved posts, syncs analytics, teaches the flywheel
  4. refreshes trend angles, runs the eval suite, plans Agent Inbox proposals
Idempotent enough to re-run: it reuses the campaign if it already exists."""

from __future__ import annotations

import os
import sys

import httpx

# Point at another deployment with DEMO_API, e.g. DEMO_API=http://121.43.99.199:8000
BASE = os.environ.get("DEMO_API", "http://127.0.0.1:8000").rstrip("/") + "/api/v1/team"

BRIEF = {
    "product_name": "TestSprite",
    "product_description": (
        "An agentic testing platform that verifies AI-generated code with live browsers and APIs."
    ),
    "target_audience": "Engineering leaders and AI-native developers using coding agents",
    "marketing_goal": "Generate qualified developer signups and API key starts",
    "brand_voice": "Confident, technical, evidence-first",
    "user_prompt": "ready for planning: launch campaign for TestSprite v2",
    "selected_channels": ["LinkedIn", "Email", "Community"],
}


def main() -> None:
    with httpx.Client(timeout=300) as http:
        members = http.get(f"{BASE}/members").json()
        lead = next(m for m in members if m["role"] == "lead" and m["kind"] == "human")
        H = {"X-Member-Id": lead["id"]}
        print(f"lead: {lead['display_name']}")

        campaigns = http.get(f"{BASE}/campaigns", headers=H).json()
        camp = next((c for c in campaigns if c["name"] == "TestSprite launch"), None)
        if camp is None:
            board = http.post(
                f"{BASE}/campaigns",
                headers=H,
                json={
                    "name": "TestSprite launch",
                    "brief": BRIEF,
                    "template": "general",
                    "event_name": "TestSprite v2 launch",
                    "event_date": "2026-07-31",
                    "review_assets": True,
                    "with_visuals": True,
                },
            ).json()
            cid = board["campaign"]["id"]
            print(f"created campaign {cid}")
        else:
            cid = camp["id"]
            print(f"reusing campaign {cid}")

        http.post(f"{BASE}/campaigns/{cid}/run", headers=H)
        board = http.get(f"{BASE}/campaigns/{cid}/board", headers=H).json()

        pending = [t for t in board["tasks"] if t["status"] == "needs_review"]
        keep = 1  # leave real work in the review queue — the demo shows human decisions
        to_approve = pending[:-keep] if len(pending) > keep else []
        for t in to_approve:
            r = http.post(
                f"{BASE}/tasks/{t['id']}/review", headers=H, json={"action": "approve"}
            )
            print(f"approved: {t['title']} ({r.status_code})")
        print(f"left in review: {min(len(pending), keep) if pending else 0}")

        for step, method, path in [
            ("publish", "POST", f"{BASE}/campaigns/{cid}/publish"),
            ("analytics sync", "POST", f"{BASE}/campaigns/{cid}/analytics/sync"),
            ("flywheel learn", "POST", f"{BASE}/insights/learn"),
            ("trend refresh", "POST", f"{BASE}/campaigns/{cid}/trends"),
            ("eval suite", "POST", f"{BASE}/evals/run"),
            ("agent inbox plan", "POST", f"{BASE}/actions/plan"),
        ]:
            r = http.request(method, path, headers=H)
            print(f"{step}: {r.status_code}")

        # Verify every demo surface has data.
        perf = http.get(f"{BASE}/campaigns/{cid}/performance", headers=H).json()
        trends = http.get(f"{BASE}/campaigns/{cid}/trends", headers=H).json()
        fleet = http.get(f"{BASE}/fleet", headers=H).json()
        queue = http.get(f"{BASE}/review-queue", headers=H).json()
        insights = http.get(f"{BASE}/insights", headers=H).json()
        published = sum(len(p.get("posts", [])) for p in perf.get("platforms", []))
        checks = {
            "published posts w/ metrics": published,
            "trend angles": len(trends),
            "fleet agents with runs": sum(1 for a in fleet if a.get("runs", 0) > 0),
            "review queue items": len(queue),
            "flywheel attributes learned": len(insights.get("attributes", []) or []),
        }
        print("\n--- demo surfaces ---")
        bad = False
        for name, n in checks.items():
            flag = "OK " if n > 0 else "EMPTY!"
            if n == 0 and name != "flywheel attributes learned":
                bad = True
            print(f"{flag:7}{name}: {n}")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
