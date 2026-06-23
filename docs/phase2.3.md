# Phase 2.3: Brand Context and Developer-Tool Campaigns

## Product angle

Phase 2.3 adapts ReelMatrix for a concrete potential customer profile: AI developer-tool companies such as TestSprite. These teams do not need generic marketing copy. They need technical, evidence-led campaign material that can speak to developers, engineering leaders, QA teams, and users of AI coding agents.

The goal is to make ReelMatrix useful in a customer demo: load the TestSprite preset, generate a developer-tool campaign package, review source-backed claims, edit draft assets, and export the package.

## In scope

- Add campaign template selection:
  - general launch
  - developer tool
- Add brand context fields:
  - target personas
  - proof points with optional source URLs
  - forbidden words
  - competitors
  - tone rules
  - source links
- Add a TestSprite demo preset for developer-tool campaigns.
- Extend campaign requests and plans with brand context and claim checks.
- Generate developer-tool assets for:
  - LinkedIn founder or technical narrative
  - X / Twitter launch thread
  - technical launch blog
  - GitHub / CLI quickstart copy
  - engineering-lead email
  - community launch note
- Mark proof-oriented claims as:
  - source-backed
  - needs validation
- Include claim checks in the workspace and Markdown export.

## Out of scope

- Web crawling or automatic source extraction
- CRM enrichment or outbound automation
- Account-based campaign sequencing
- Product telemetry or analytics collection
- Automated publishing to GitHub, X, LinkedIn, email, or communities
- Legal approval workflows
- Multi-user review comments

## Acceptance criteria

1. A user can choose the developer-tool campaign template.
2. A user can load the TestSprite demo preset.
3. The submitted request includes brand context and proof points.
4. Mock generation returns a developer-tool campaign package when the template is selected.
5. Generated plans include claim checks for source-backed and needs-validation claims.
6. The workspace shows claim checks before market adaptation and draft assets.
7. Markdown export includes claim checks.
8. Backend and frontend tests cover the new request fields, output fields, form behavior, and export behavior.

## Recommended next phase

Phase 2.4 should improve the quality of the generated package rather than add infrastructure. Good options:

- add per-asset regenerate instructions
- add a claim-review checklist before export
- add `.docx` or content-calendar export
- add a customer demo page preloaded with TestSprite context
- add source snippets so users can paste exact lines from websites or articles
