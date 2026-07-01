# Demo script — the five-minute hook (≈3 min) + the team beneath (≈1.5 min)

Run locally for demos (fast + wifi-proof with the mock provider, or plug a real key):

```bash
# one-time seed
rm -f /tmp/rm_demo.db
DATABASE_URL=sqlite:////tmp/rm_demo.db LLM_PROVIDER=mock uv run python -m core.db.seed

# terminal 1 — API (swap LLM_PROVIDER=dashscope|openai + key in .env for a live model)
DATABASE_URL=sqlite:////tmp/rm_demo.db LLM_PROVIDER=mock WEB_ORIGIN=http://localhost:3000 \
  uv run uvicorn apps.api.main:app --port 8000

# terminal 2 — web
cd apps/web && npm run dev
```

Open http://localhost:3000 → it lands on **Strategy**. The badge in the top bar shows which
model is live ("live on mock (offline demo)" / "live on Qwen · qwen-plus") — one env var
swaps it; that's the provider-factory story.

## Beat 1 — "I have an idea, not a strategy" (the hook)

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

5. **Open in workspace →** the drafts live in **Create** as normal tasks. Click one: full
   detail — checks (format / brand / terminology / audit), versions, comments, reassign.
6. Top bar: **switch "acting as" Adam (Lead) → Sam (Writer)** — same system, role-scoped
   views: the lead sees the cross-campaign review queue ("Needs you"), the writer sees only
   their tasks. AI teammates are just members here — same assignment, same review gates.
   > "Every AI draft is reviewable, editable, and attributable. Humans decide; the AI team
   > does the drafting and the checking (a cross-model Auditor audits the copywriter)."
7. (Optional) **Team** tab — the org: human + AI employees, who handles what, per-agent
   run stats. Hiring an AI employee = config, not code.

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
