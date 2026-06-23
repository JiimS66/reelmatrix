# Phase 2.1: Editable AI Campaign Package

## Product angle

ReelMatrix is now positioned as an AI Campaign Studio for small teams and cross-border founders. A user enters the product, target market, audience, goal, channels, and language, chooses Local, Qwen, GPT, or Mock, and receives an editable campaign package.

The package should help a small team move from product context to first-pass execution material without needing a full marketing function.

## In scope

- Cross-border campaign brief fields:
  - target market
  - output language
  - campaign duration
  - selected channels
- Campaign plan generation remains compatible with the Phase 1 workflow.
- Campaign plan responses can include:
  - market adaptation notes
  - first-draft channel assets
- Frontend workspace supports:
  - editing generated asset titles, copy, and calls to action
  - copying the full package as Markdown
  - exporting the full package as a Markdown file
- Mock provider returns deterministic Phase 2.1 output for local demos and tests.
- CI runs backend tests, frontend typecheck, frontend tests, and frontend production build.

## Out of scope

- Database persistence
- Authentication
- User accounts or multi-tenant workspaces
- Real social posting or email sending
- CRM integration
- RAG or uploaded brand knowledge
- Background workers and scheduling
- Payment or subscription flows

## Acceptance criteria

1. A user can select target market, output language, campaign duration, and channels.
2. A mock campaign request returns a plan, market adaptation, and draft assets.
3. Draft assets are editable in the browser.
4. The full campaign package can be copied as Markdown.
5. The full campaign package can be downloaded as Markdown.
6. Existing model routing remains intact for mock, local, OpenAI, and DashScope/Qwen.
7. CI is present for backend and frontend checks.

## Recommended next phase

Phase 2.2 should focus on quality and usefulness, not infrastructure. The most useful next steps are:

- add per-asset regenerate actions
- add a simple localStorage campaign history
- add better examples for SaaS, AI tools, ecommerce, and agencies
- add a brand context section with tone, forbidden words, competitors, and proof points
- add a visual review pass for the Campaign Studio layout
