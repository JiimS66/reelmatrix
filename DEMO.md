# Demo script — the five-minute hook (≈3 min) + the team beneath (≈1.5 min) + the full tour (≈4 min)

Run locally. Two modes — **real Qwen** (impressive copy; the strategy turn takes ~15–25s
and the lock→content handoff ~60s, both covered by the thinking/pipeline UI) or **mock**
(instant + wifi-proof — the fallback if the venue network dies):

```bash
# one-time seed + full-feature demo data (every tab alive; leaves work in the review queue)
rm -f /tmp/rm_demo.db
DATABASE_URL=sqlite:////tmp/rm_demo.db LLM_PROVIDER=mock uv run python -m core.db.seed

# terminal 1 — API · REAL QWEN (recommended for the live hook; key stays in env, never in git)
DATABASE_URL=sqlite:////tmp/rm_demo.db LLM_PROVIDER=dashscope \
  DASHSCOPE_API_KEY=$DASHSCOPE_API_KEY \
  DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 DASHSCOPE_MODEL=qwen-plus \
  WEB_ORIGIN=http://localhost:3000 uv run uvicorn apps.api.main:app --port 8000
# … or MOCK (offline fallback): drop the DASHSCOPE_* vars and use LLM_PROVIDER=mock

# terminal 2 — web
cd apps/web && npm run dev

# terminal 3 — pump the demo data (campaign run + approvals + publish + metrics + trends + evals)
uv run python scripts/demo_prep.py
```

Open http://localhost:3000 → it lands on **Home**, the role-aware desk (lead = approvals
across campaigns; writer = their own tasks). The top-bar badge shows which model is live
("live on mock (offline demo)" / "live on Qwen · qwen-plus") — one env var swaps it;
that's the provider-factory story.

## Beat 1 — "I have an idea, not a strategy" (the hook)

0. **Click "✨ New campaign from an idea"** — the strategy copilot opens. (A brand-new
   tenant lands here automatically — thinking the strategy through IS onboarding.)
1. **Click the first suggestion chip** — *"An agentic testing platform that verifies
   AI-generated code"* (yes, that's TestSprite — the demo customer is the audience).
2. **Think it through** → the advisor drafts a one-page strategy live: what it heard,
   **where it had to guess** (assumptions called out), 3 audience candidates + 3 positioning
   angles — each tagged *my guess / likely / you confirmed*. Point at the tags:
   > "It offers options for you to recognize, not a form to fill. And it tells you what it's
   > unsure about."
3. **React once** — click an audience card (or type "Target is solo founders"), hit
   **Refine with this** → the draft re-thinks around your steer; "How we got here" logs the
   turn. That's the loop: react → it re-thinks → guesses become confirmations.
4. **Lock it → draft my first content** → watch the pipeline: *Ideation → Planning →
   Copywriter per channel → Auditor*. Then the reveal: **native-looking LinkedIn / email /
   community drafts**, each stamped *"Drafted by your AI copywriter · Auditor ✓ clean ·
   waiting on a human — you."*
   > "Idea to reviewed cross-channel drafts, in one sitting. Locking the strategy also
   > reshaped the brand's operating context — audience → ICP segment, angle → value prop —
   > so everything downstream inherits it."

## Beat 2 — "and this works with a real marketing team" (human ↔ AI)

TestSprite has a real marketing team — this is the part built for them.

5. **Open in workspace →** the campaign opens on its **Board**: a pipeline kanban
   (Plan → Draft → In review → Approved) where **every card is stamped with its owner** —
   a human avatar (Adam's claim-check) or an AI ⚙ mark (Ideation / Planning / the
   copywriters). Division of labor at a glance. Click a card: full detail — checks,
   versions, comments, reassign.
6. Top bar: **switch "acting as" Adam (Lead) → Sam (Writer)** — same system, role-shaped
   desks: the lead's Home is the cross-campaign approvals queue ("Needs you"), the
   writer's Home is their own task list. AI teammates are just members here — same
   assignment, same review gates.
   > "Every AI draft is reviewable, editable, and attributable. Humans decide; the AI team
   > does the drafting and the checking (a cross-model Auditor audits the copywriter)."
7. (Optional) **Team** tab — the org: human + AI employees, who handles what, per-agent
   run stats. Hiring an AI employee = config, not code.

## Beat 3 — the full tour (after `scripts/demo_prep.py`, every tab is alive)

Open **Campaigns → "TestSprite launch"** (the pre-pumped project) and walk the tabs:

8. **Board** — a campaign mid-flight: Plan done, drafts approved, **one post still in
   review + the fact-check (claim-check) waiting on Adam** — the truth rail: numbers and
   claims need a source before publishing.
9. **Calendar** — the event countdown (milestones toward the launch date) + **trend
   angles**, each scored for brand fit with a **brand-safety kill-switch** (a tragedy/
   sensitive topic can never be drafted); click *"Draft a rapid post"* on a safe one —
   a timely post lands in the pipeline, always human-review-gated.
10. **Results** — published posts with per-platform metrics (impressions → clicks →
    signups), *Sync GA4* (provider-mocked, same interface as real), and below it the
    **growth layer**: what the flywheel learned (attribute → outcome priors that feed
    back into generation), experiments, funnel coverage.
11. **Brand** — the operating context every agent reads: the **value proposition +
    pillars imprinted by the locked strategy**, ICP segments (who/pains/platforms),
    terminology (banned/preferred words enforced as checks).
12. **Team** — the duty roster: humans + AI employees, who handles which task kinds,
    per-agent runs/scores/self-corrections; **hire or reconfigure an AI employee** live
    (config, not code). Reliability scorecard = autonomy is *earned* (an agent only gets
    auto-publish rights after enough clean runs).
13. **⌘K** anywhere — jump around like a power user.

Closing line: *"Strategy in, reviewed content out, results feeding back — one loop,
humans deciding, AI doing the legwork, every step auditable."*

## Reset between runs

Click **Start over** in the Strategy panel (fully resets the panel). For a pristine
workspace, reseed: `rm -f /tmp/rm_demo.db && DATABASE_URL=... uv run python -m core.db.seed`
(command above) and restart the API.

## One-liners for questions

- **Why not just ChatGPT?** The value is above the model: memory (brand/ICP/episodic),
  a closed loop (strategy → content → review → measure), guardrails (brand/policy/audit),
  and a team OS — the model is swappable (that badge).
- **What's real?** The strategy loop + handoff + team OS run end-to-end on a real LLM
  (Qwen/OpenAI by env). Analytics/publishing are provider-mocked by design — same
  interfaces, swap-in integrations.
- **Tested how?** 199 backend + 6 frontend tests, plus TestSprite CLI runs against the
  live deployment — the fail→fix→rerun log is in [LOOP.md](LOOP.md).
