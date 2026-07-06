# Architecture — the Enterprise Loop (team-os phase 1)

Scope agreed on 2026-07-05 from TestSprite (first prospective customer + hackathon
host) feedback and a UX/marketing/frontend review. Five workstreams, one theme:
**make the loop connect to the customer's real operating stack — their OA board,
their funnel, their channels — and show it visually instead of in prose.**

Everything follows the house pattern: *abstract interface + deterministic mock +
factory*, so the whole product still runs offline with zero keys.

## 1. Channel layer — the AI knows which platforms you actually run

TestSprite's favorite feature is auto-splitting a campaign into per-platform
tasks. The risk they flagged: how does the AI know which platforms we operate,
what ran there before, and how to stay consistent?

- **`ChannelProfile`** (new table): tenant-level registry — platform, handle,
  audience note, cadence, `active`. Managed in the Brand tab. The campaign
  instantiation only assigns asset tasks to **active** channels.
- **Channel history injection**: `_copywriter_context()` gains
  `channel_history` — the last N published posts on the same platform — so the
  next LinkedIn post knows the previous five (continuity), plus the channel's
  handle/audience note (fit).
- **Continuity check**: a deterministic check flags a draft whose headline/hook
  overlaps too heavily with a recent post on the same channel.
- Segment→channel routing already exists (`IcpSegment.platforms`); it now reads
  from the same active-channel registry.

## 2. Linear timeline sync — the campaign schedule lives in the customer's OA

Today `/integrations/dispatch` pushes one manual issue. The customer ask is
centralized management: the whole launch timeline in Linear.

- **`ExternalLink`** (new table): `local_kind/local_id ↔ provider/external_id/url`
  mapping — the idempotency backbone. Re-sync updates, never duplicates.
- **`POST /integrations/linear/sync-campaign`**: campaign → a Linear **project**;
  every dated task → an **issue** with `dueDate`, description (channel, status,
  content preview), upserted via ExternalLink. One-way push v1 (ReelMatrix is the
  source of truth); status webhooks are a later phase.
- Credentials stay request-scoped (never persisted) — same posture as today.
- Generic webhook dispatch remains the escape hatch for Feishu/DingTalk/OA.

## 3. ROI — first-party, funnel-shaped, honestly labeled

B2B dev-tool attribution is *content → signup → activation → paid*, first-party
UTM + product events — not coupon codes or 3rd-party cookies (industry direction:
S2S/CAPI + modeled conversions).

- **Funnel stages**: `MetricSnapshot` gains `activations`, `paid`. Mock derives
  them deterministically; the analytics ABC carries them end-to-end.
- **`ConversionEvent`** (new table) + **`POST /api/v1/events/{tenant_id}`**: an
  S2S postback-style first-party ingest. The customer's backend fires
  signup/activation/paid events tagged with the UTM content id; when real events
  exist for a post they override the mock/GA4 numbers.
- **UTM links**: already minted per post (`utm_content` = task id prefix);
  now surfaced in the UI with one-click copy.
- **Honesty rule**: the dashboard is labeled `last-touch · modeled` — no
  multi-touch theater.

## 4. Trend agent (thin) — always-on brand loop with a quality funnel

Between launches the brand should stay alive. The anti-slop design is a funnel of
cheap gates; a proposal reaches a human only after passing all of them:

1. **Real source, free API**: Hacker News (Algolia) behind the existing
   `TrendSource` ABC; mock stays the default/test source. No scraping.
2. **Relevance gate**: brand-keyword scoring (existing `angle_safety`) + the
   sensitivity hard-veto.
3. **Bridge test**: a proposal must carry a "why us, why now" line; no credible
   bridge → dropped.
4. **Quota + expiry**: max 3 trend proposals/day, auto-expire after 72h.
5. **Adaptive throttle**: acceptance rate of recent trend proposals < 30% →
   quota drops to 1/day. The agent self-regulates instead of spamming.
6. Proposals surface as `PlannedAction`s in the existing Agent Inbox (zero new
   navigation); Accept runs the existing draft-from-trend flow.

## 5. Media providers — Qwen family, API + open weights

Decision (verified 2026-07): **DashScope Qwen-Image** for cloud generation,
**Z-Image-Turbo** (6B, Apache 2.0, 16GB VRAM) as the on-prem option,
**Qwen3-VL** for understanding/critique. Video stays human-shot; AI works
pre-shoot (briefs/storyboards) and post-shoot (understanding/packaging).

- `core/media/dashscope.py`: `DashScopeMediaProvider` (image gen via DashScope),
  `DashScopeVisionProvider` (Qwen3-VL critique/understanding via the
  OpenAI-compatible endpoint).
- `core/media/zimage.py`: local Z-Image-Turbo server client (`ZIMAGE_BASE_URL`).
- Settings: `MEDIA_PROVIDER` / `VISION_PROVIDER` (default `mock`);
  `_run_visual_critique` reads the setting instead of hardcoding mock.

## 6. Frontend density pass — numbers and shapes before sentences

- **Launch Timeline**: the campaign hero view — channel swimlanes, posts as
  status-colored nodes on a date axis, milestones underneath. Doubles as the
  visual for the Linear sync (chips link to synced issues).
- **Home KPI band**: needs-you count · scheduled this week · modeled pipeline ·
  best channel — numbers first, one line each.
- **TaskDetailPanel**: structured copy editor + native preview on top; the raw
  JSON moves behind an "Advanced" toggle.
- **Agent Inbox**: rationale collapsed by default.
- **Performance**: per-channel funnel (signup→activation→paid), platform bar
  click filters the post table, UTM copy per post, `last-touch · modeled` badge.
- House rule (DESIGN.md): card explainer text ≤ 1 line; prefer number/badge/chart.

## Sequencing

| # | Work | Priority |
|---|------|----------|
| 1 | DB models + seed (ChannelProfile, ExternalLink, ConversionEvent, funnel fields) | P0 |
| 2 | Channel context injection + planner filter + continuity check | P0 |
| 3 | Linear sync-campaign endpoint + UI | P0 |
| 4 | ROI funnel + events ingest + Performance UI | P1 |
| 5 | Launch Timeline + density pass | P1 |
| 6 | Trend agent thin slice | P1.5 |
| 7 | Media providers (DashScope/Z-Image/Qwen3-VL) | P1.5 |

No migrations (dev posture): delete the SQLite file and re-seed after model
changes.
