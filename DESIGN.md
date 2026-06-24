# DESIGN.md — ReelMatrix workspace

Design system for `apps/web` (the human-AI marketing team OS). Drop-in guidance
for humans and coding agents so new UI matches what exists. Inspired by
[Refactoring UI](https://refactoringui.com/) and the visual language of
testsprite.com.

## 1. Visual theme & atmosphere

Calm, technical, developer-trust. A warm off-white canvas, near-black ink, one
forest-green accent, and **monospace for technical/data labels**. Generous
whitespace; precise, not busy. The product is an operations dashboard — clarity
and "what needs me" beat decoration.

## 2. Color palette & roles

Tokens live in `tailwind.config.ts`. Use semantic roles, not raw hex.

| Token | Hex | Role |
|---|---|---|
| `canvas` | `#f4f6ef` | Page background (warm off-white) |
| `ink` | `#10211b` | Primary text, dark surfaces |
| `black` | `#0c0d0a` | Top bar, primary buttons |
| `forest` | `#3f6e1f` | **The** accent: links, key numbers, mono labels, active state |
| `moss` | `#1f6f52` | Secondary green (sparingly) |
| `lime` / `coral` | `#d7f075` / `#ff7657` | Reserved highlights; rare |

- One accent only (`forest`). Don't introduce new accent hues.
- Text hierarchy by **opacity of ink**: primary `text-ink`, secondary
  `text-ink/60`, hint `text-ink/50`. De-emphasize secondary rather than
  over-styling primary (Refactoring UI).

**Status colors (must read at a glance)** — every task surface carries a colored
left border via `statusAccent()`:

| Status | Accent | Badge |
|---|---|---|
| `done` | emerald | emerald |
| `needs_review` | amber | amber |
| `in_progress` | amber (light) | amber |
| `blocked` | red | red |
| `todo` | slate (neutral) | neutral |

Done = green, anything incomplete = amber/neutral, blocked/overdue = red. Keep
this mapping consistent everywhere (cards, calendar chips, badges).

## 3. Typography

- Sans (default, Anthropic/Inter-like) for prose and headings; **`font-mono`**
  for technical labels, IDs, dates, metrics, statuses.
- Hierarchy from **weight + color + size**, not size alone. Two weights: 400 and
  600 (`font-semibold`). Avoid <400.
- Scale (non-linear): page h1 `text-2xl`, section `text-lg`, body `text-sm`,
  labels `text-[11px]`–`text-[12px]`.
- `.tlabel` = the eyebrow/label style (mono, 11px, forest). Sentence case, never
  ALL CAPS. Right-align numbers in tables.

## 4. Components

Defined in `app/globals.css`. Reuse them; don't reinvent.

- `.surface` — card: white, thin `border-ink/10`, `rounded-2xl`, `shadow-soft`.
- `.chip` — rounded-full mono tag for metadata (assignee, mode).
- Buttons: `.btn-dark` (black→forest on hover, primary), `.btn-green` (forest,
  affirmative e.g. Approve), `.btn-line` (outline, secondary).
- `.field` — input/textarea/select (forest focus ring).
- `.tlabel` — section eyebrow.
- Tabs: active = `bg-ink text-white`; inactive = white with thin border.

## 5. Layout & spacing

- Base unit 4px; steps ~`gap-2/3/5/6`. Space **between** groups exceeds space
  **within** a group.
- Content max width `max-w-6xl`, comfortable page padding (`px-5 py-7`).
- Master-detail: list/agenda left, a sticky context/detail pane right
  (`lg:grid-cols-2`, `lg:sticky lg:top-6`).
- Use more whitespace than feels necessary.

## 6. Depth & elevation

- Prefer **shadow + background change over borders** for separation
  (`shadow-soft`). Thin borders only for definition.
- Subtle only — no heavy drop shadows, gradients, or glow. The page has a faint
  `gridbg` graph-paper texture; keep surfaces flat white on top.

## 7. Guardrails (do / don't)

- Do: one accent, opacity-based text hierarchy, mono for data, consistent status
  colors, lots of whitespace.
- Don't: ALL CAPS, second accent hue, font-weight <400, oversized icons (>2–3×),
  cramming the nav (keep ≤5–6 top-level tabs), dumping completed items into
  to-do lists (completed work belongs on the calendar/board, not the agenda).

## 8. Responsive

- Mobile-first; stack the master-detail to one column below `lg`.
- Status bar and stat grids wrap (`flex-wrap`, `grid-cols-2 sm:grid-cols-4`).
- Touch targets ≥ ~36px; nav wraps rather than truncates.

---

### Agent prompt guide

> Build/modify `apps/web` UI to match DESIGN.md: warm `canvas` background, `ink`
> text with opacity-based hierarchy, a single `forest` accent, `font-mono` for
> technical labels, `.surface`/`.chip`/`.btn-*`/`.field` components, and the
> status color mapping (done=emerald, review/in-progress=amber, blocked=red,
> todo=neutral) via `statusAccent()`. Favor whitespace and clarity over density.

---

## Media / visual generation (planned)

Built-in, locally-deployable image generation behind a **swappable provider** — design
the abstraction now so a model upgrade is a config swap, not a rewrite.

- **Models (open-weight):** default **HiDream-O1-Image** (MIT, commercial-free; one
  checkpoint does text-to-image + instruction editing + subject-driven personalization).
  Alternative **Ideogram 4.0** (best in-image text + palette/layout control; commercial
  self-host needs an Ideogram license). Also viable: Qwen-Image (Apache-2.0), FLUX.2
  (license-gated), SDXL (deepest LoRA/ControlNet/IP-Adapter ecosystem).
- **Abstraction (mirror the LLM provider factory):** `MediaProvider.generate_image(prompt,
  brand, refs, controls)` + `VisionProvider.understand(media)`; impls local
  (ComfyUI / diffusers / vLLM) | hosted (Fal / Replicate / DashScope / Ideogram) | mock.
  Model upgrade = swap the provider.
- **Brand consistency:** LoRA (brand style) + IP-Adapter (reference images) + ControlNet
  (layout templates) + native subject-driven personalization. Extend `BrandProfile` with a
  visual identity (palette, logo, fonts, reference images, brand LoRA) and add a visual
  consistency check (palette/logo + VLM-judge), mirroring the text format/brand/consistency
  checks.
- **Multimodal input:** a VLM reads a human-provided image / video frame / doc → brief +
  references that feed the content core and the image pipeline.
- A `Designer` digital-employee role calls these providers; `visual` tasks route to the AI
  or a human designer (org-configurable). Video stays human for now (same interface leaves
  a slot for a video model later).
