"use client";

import { useEffect, useState } from "react";

import {
  advanceStrategySession,
  handoffStrategySession,
  startStrategySession,
  type Board,
  type StrategySession,
} from "@/lib/teamApi";

/** Circuit A — the strategy co-creation loop, made tangible. The marketer feeds whatever
 * they have; the advisor makes its best guess, FLAGS what it's unsure of (confidence +
 * assumptions), and they sharpen it turn by turn. The point is to RECOGNIZE the right
 * strategy (react to options) rather than invent it — and to feel the loop: react → it
 * re-thinks → the draft sharpens, guesses turn into confirmations. Locking hands off to
 * circuit B: the AI team drafts the first content while the marketer watches the stages. */

// One-click ways in — the first chip is the hackathon demo (TestSprite-flavored).
const IDEA_CHIPS = [
  "An agentic testing platform that verifies AI-generated code",
  "An AI copilot that drafts marketing emails for small teams",
  "An open-source CLI that turns design tokens into production code",
];

// What the advisor is "doing" while a turn runs — honest stage names, paced for reading.
const THINKING = [
  "Reading what you gave me…",
  "Pulling industry priors…",
  "Sketching audience candidates…",
  "Weighing positioning angles…",
  "Marking what I'm unsure of…",
];

// Mirrors the backend platform-spec registry so the pipeline lists only channels that will
// actually render (unknown channels are dropped server-side).
const KNOWN_CHANNELS = new Set([
  "linkedin",
  "x / twitter",
  "email",
  "blog",
  "github / cli",
  "landing page",
  "community",
]);

function Confidence({ c }: { c: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    guess: { label: "my guess", cls: "bg-ink/10 text-ink/55" },
    likely: { label: "likely", cls: "bg-amber-100 text-amber-700" },
    confirmed: { label: "you confirmed", cls: "bg-forest/15 text-forest" },
  };
  const m = map[c] ?? map.guess;
  return (
    <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] ${m.cls}`}>
      {m.label}
    </span>
  );
}

function ThinkingStrip({ step }: { step: number }) {
  return (
    <span className="inline-flex items-center gap-2 font-mono text-xs text-forest">
      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-forest border-t-transparent" />
      {THINKING[step % THINKING.length]}
    </span>
  );
}

/** First content rendered as native-looking previews — the reveal should feel like real
 * posts landing, not database rows. */
function PlatformCard({
  brand,
  channel,
  title,
  body,
  cta,
}: {
  brand: string;
  channel: string;
  title: string;
  body: string;
  cta: string;
}) {
  const c = channel.toLowerCase();
  const avatar = (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-forest text-sm font-semibold text-white">
      {brand.charAt(0).toUpperCase()}
    </div>
  );
  if (c.includes("linkedin")) {
    return (
      <div className="overflow-hidden rounded-xl border border-ink/12 bg-white">
        <div className="flex items-center gap-2.5 px-4 pt-3.5">
          {avatar}
          <div>
            <p className="text-sm font-semibold text-ink">{brand}</p>
            <p className="text-[11px] text-ink/45">LinkedIn · just now</p>
          </div>
        </div>
        <p className="whitespace-pre-wrap px-4 py-3 text-sm leading-relaxed text-ink/85">
          {body}
        </p>
        {cta && (
          <div className="mx-4 mb-3 inline-block rounded-full border border-forest px-3 py-1 text-xs font-medium text-forest">
            {cta}
          </div>
        )}
        <div className="border-t border-ink/8 px-4 py-2 font-mono text-[11px] text-ink/40">
          Like · Comment · Repost · Send
        </div>
      </div>
    );
  }
  if (c.includes("email")) {
    return (
      <div className="overflow-hidden rounded-xl border border-ink/12 bg-white">
        <div className="space-y-1 border-b border-ink/8 bg-ink/[0.03] px-4 py-2.5 text-xs">
          <p className="text-ink/55">
            <span className="font-mono text-ink/40">From:</span> {brand}
          </p>
          <p className="font-medium text-ink">
            <span className="font-mono font-normal text-ink/40">Subject:</span>{" "}
            {title || body.slice(0, 60)}
          </p>
        </div>
        <p className="whitespace-pre-wrap px-4 py-3 text-sm leading-relaxed text-ink/85">
          {body}
        </p>
        {cta && (
          <div className="mx-4 mb-3 inline-block rounded-lg bg-forest px-3.5 py-1.5 text-xs font-medium text-white">
            {cta}
          </div>
        )}
      </div>
    );
  }
  if (c.includes("twitter") || c === "x") {
    const handle = brand.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 12) || "brand";
    return (
      <div className="rounded-xl border border-ink/12 bg-white p-4">
        <div className="flex gap-2.5">
          {avatar}
          <div className="min-w-0">
            <p className="text-sm">
              <span className="font-semibold text-ink">{brand}</span>{" "}
              <span className="text-ink/40">@{handle} · now</span>
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink/85">
              {body}
            </p>
            {cta && <p className="mt-2 text-xs text-forest">{cta}</p>}
          </div>
        </div>
      </div>
    );
  }
  if (c.includes("community")) {
    return (
      <div className="rounded-xl border border-ink/12 bg-white p-4">
        <p className="font-mono text-[11px] text-ink/45">community · posted by {brand}</p>
        {title && <p className="mt-1.5 text-sm font-semibold text-ink">{title}</p>}
        <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink/85">{body}</p>
        {cta && <p className="mt-2 text-xs text-forest">{cta} →</p>}
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-ink/12 bg-white p-4">
      <p className="font-mono text-xs text-forest">{channel}</p>
      {title && <p className="mt-1 text-sm font-semibold text-ink">{title}</p>}
      <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink/85">{body}</p>
      {cta && <p className="mt-1.5 text-xs text-forest">CTA: {cta}</p>}
    </div>
  );
}

export function StrategyAdvisorPanel({
  memberId,
  onOpenContent,
}: {
  memberId: string;
  onOpenContent?: (board: Board) => void;
}) {
  const [idea, setIdea] = useState("");
  const [session, setSession] = useState<StrategySession | null>(null);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<Board | null>(null);
  const [thinkStep, setThinkStep] = useState(0);
  const [reveal, setReveal] = useState(99); // sections visible by default; animated per draft
  const [handoffStage, setHandoffStage] = useState(-1); // -1 = not handing off

  const draft = session?.draft ?? null;
  const firstPosts = (content?.tasks ?? []).filter((t) => t.kind === "asset" && t.output);
  const brandName =
    (content?.campaign.name ?? "Your brand")
      .split(/\s+/)
      .slice(0, 4)
      .join(" ")
      .slice(0, 26) || "Your brand";

  // Cycle the "what I'm doing" line while a turn runs.
  useEffect(() => {
    if (!busy) return;
    setThinkStep(0);
    const t = setInterval(() => setThinkStep((s) => s + 1), 1200);
    return () => clearInterval(t);
  }, [busy]);

  // Progressive reveal: each new draft fades in section by section instead of popping.
  useEffect(() => {
    if (!session?.draft) return;
    setReveal(0);
    let step = 0;
    const t = setInterval(() => {
      step += 1;
      setReveal(step);
      if (step >= 6) clearInterval(t);
    }, 200);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.turn_count]);

  const veil = (step: number) =>
    `transition-all duration-500 ${reveal >= step ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"}`;

  // The stages the marketer watches during the A→B handoff — same order as the backend.
  const stageChannels = (draft?.channels ?? []).filter((c) =>
    KNOWN_CHANNELS.has(c.trim().toLowerCase()),
  );
  const handoffStages = [
    "Ideation — sharpening the concept",
    "Planning — locking one core message",
    ...(stageChannels.length ? stageChannels : ["LinkedIn", "Email"]).map(
      (c) => `Copywriter — drafting ${c}`,
    ),
    "Auditor — checks & brand review",
  ];

  async function run(fn: () => Promise<StrategySession>) {
    setBusy(true);
    setError(null);
    try {
      setSession(await fn());
      setFeedback("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  const start = () =>
    idea.trim() &&
    run(() => startStrategySession(memberId, [{ type: "idea", value: idea.trim() }]));
  const advance = () =>
    session &&
    feedback.trim() &&
    run(() => advanceStrategySession(memberId, session.id, { feedback: feedback.trim() }));

  // The five-minute hook: lock the strategy AND draft the first content from it in one
  // move. While the backend pipeline runs (ideation → plan → per-channel drafts → audit),
  // the UI walks the same stages so the marketer watches their AI team work, not a spinner.
  async function lockAndCreate() {
    if (!session) return;
    setBusy(true);
    setError(null);
    setHandoffStage(0);
    const timer = setInterval(
      () => setHandoffStage((s) => Math.min(s + 1, handoffStages.length - 1)),
      1100,
    );
    try {
      const board = await handoffStrategySession(memberId, session.id, {
        review_assets: false,
      });
      clearInterval(timer);
      setHandoffStage(handoffStages.length); // everything done
      setContent(board);
      setSession({ ...session, status: "done", campaign_id: board.campaign.id });
    } catch (e) {
      clearInterval(timer);
      setHandoffStage(-1);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setSession(null);
    setIdea("");
    setFeedback("");
    setContent(null);
    setHandoffStage(-1);
    setError(null);
  }

  return (
    <div className="space-y-5">
      {/* The ask */}
      <div className="surface p-6">
        <p className="tlabel">Strategy co-creation · loop A</p>
        <h2 className="mt-1 text-lg text-ink">Let&apos;s think your strategy through</h2>
        <p className="mt-1 max-w-2xl text-sm text-ink/60">
          Tell me what you want to take to market — a sentence is enough. I&apos;ll make my
          best guess, flag what I&apos;m unsure of, and we sharpen it together. No form to fill.
        </p>
        <textarea
          className="mt-3 w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm disabled:bg-ink/5"
          rows={3}
          placeholder="e.g. I built an AI tool that proofreads marketing copy for small teams…"
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          disabled={!!session}
        />
        {!session && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {IDEA_CHIPS.map((c) => (
              <button
                key={c}
                className="rounded-full border border-ink/15 px-2.5 py-1 text-xs text-ink/55 transition hover:border-forest/40 hover:text-ink"
                onClick={() => setIdea(c)}
              >
                {c}
              </button>
            ))}
          </div>
        )}
        <div className="mt-3 flex items-center gap-3">
          {!session ? (
            <>
              <button
                className="rounded-lg bg-forest px-4 py-2 text-sm text-white transition hover:bg-forest/90 disabled:opacity-50"
                disabled={busy || !idea.trim()}
                onClick={start}
              >
                {busy ? "Thinking…" : "Think it through"}
              </button>
              {busy && <ThinkingStrip step={thinkStep} />}
            </>
          ) : (
            <>
              <span className="font-mono text-xs text-ink/45">
                turn {session.turn_count} · {session.status}
              </span>
              <button className="btn-line px-3 py-1.5 text-xs" onClick={reset}>
                Start over
              </button>
            </>
          )}
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>
      </div>

      {draft && (
        <>
          {/* Understanding */}
          <div className={`surface border-l-2 border-forest p-5 ${veil(1)}`}>
            <p className="tlabel">What I heard</p>
            <p className="mt-1 text-[15px] leading-relaxed text-ink">{draft.understanding}</p>
          </div>

          {/* Assumptions — the guesses it flagged, so the loop never stalls on missing info */}
          {draft.assumptions.length > 0 && (
            <div className={`rounded-lg border border-amber-200 bg-amber-50 p-4 ${veil(2)}`}>
              <p className="tlabel text-amber-800">Where I had to guess</p>
              <ul className="mt-1.5 space-y-1">
                {draft.assumptions.map((a, i) => (
                  <li key={i} className="text-sm text-amber-900">
                    {a}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-amber-700">
                If any of this is off, just tell me below and I&apos;ll redo it.
              </p>
            </div>
          )}

          {/* Audience candidates — click to pick, or correct me below */}
          <div className={`surface p-5 ${veil(3)}`}>
            <p className="tlabel">Who it&apos;s really for — click the closest</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {draft.audience_candidates.map((a, i) => (
                <button
                  key={i}
                  onClick={() => setFeedback(`The audience is "${a.name}" — focus there.`)}
                  className="rounded-lg border border-ink/12 p-3 text-left transition hover:border-forest/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-ink">{a.name}</p>
                    <Confidence c={a.confidence} />
                  </div>
                  <p className="mt-1 text-xs text-ink/60">{a.why}</p>
                  <p className="mt-1.5 text-xs text-forest">Pain: {a.pain}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Angles */}
          <div className={`surface p-5 ${veil(4)}`}>
            <p className="tlabel">Angles to stand out — which feels like you?</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {draft.positioning_angles.map((a, i) => (
                <button
                  key={i}
                  onClick={() => setFeedback(`Let's go with the angle "${a.angle}".`)}
                  className="rounded-lg border border-ink/12 p-3 text-left transition hover:border-forest/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-ink">{a.angle}</p>
                    <Confidence c={a.confidence} />
                  </div>
                  <p className="mt-1 text-xs text-ink/60">{a.rationale}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Pillars / channels / measure */}
          <div className={`grid gap-5 sm:grid-cols-2 ${veil(5)}`}>
            <div className="surface p-5">
              <p className="tlabel">Content pillars</p>
              <ul className="mt-2 space-y-1.5">
                {draft.content_pillars.map((p, i) => (
                  <li key={i} className="flex gap-2 text-sm text-ink">
                    <span className="font-mono text-xs text-forest">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
              <p className="tlabel mt-4">Channels</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {draft.channels.map((c) => (
                  <span
                    key={c}
                    className="rounded-full border border-ink/15 px-2.5 py-0.5 text-xs text-ink/70"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
            <div className="surface p-5">
              <p className="tlabel">How we&apos;ll know it&apos;s working</p>
              <p className="mt-2 text-sm leading-relaxed text-ink">{draft.measure}</p>
            </div>
          </div>

          {/* Next questions */}
          <div className={`surface p-5 ${veil(6)}`}>
            <p className="tlabel">What I&apos;d ask you next</p>
            <ul className="mt-2 space-y-2">
              {draft.next_questions.map((q, i) => (
                <li key={i} className="flex gap-2 text-sm text-ink/80">
                  <span className="text-forest">→</span>
                  <span>{q}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* The loop — react and iterate, lock it, or watch the team work */}
          {handoffStage >= 0 && !content ? (
            <div className="surface border border-forest/30 p-5">
              <p className="tlabel">Your AI team is on it</p>
              <ul className="mt-3 space-y-2">
                {handoffStages.map((s, i) => (
                  <li key={s} className="flex items-center gap-2.5 text-sm">
                    {i < handoffStage ? (
                      <span className="text-forest">✓</span>
                    ) : i === handoffStage ? (
                      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-forest border-t-transparent" />
                    ) : (
                      <span className="mx-1 inline-block h-1.5 w-1.5 rounded-full bg-ink/20" />
                    )}
                    <span className={i <= handoffStage ? "text-ink" : "text-ink/40"}>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : session?.status !== "done" ? (
            <div className={`surface border border-forest/30 p-5 ${veil(6)}`}>
              <p className="tlabel">Your turn — correct me, answer, or add anything</p>
              <textarea
                className="mt-2 w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
                rows={2}
                placeholder="e.g. Target is solo founders, not teams · or click an option above"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              />
              <div className="mt-3 flex items-center gap-3">
                <button
                  className="rounded-lg bg-forest px-4 py-2 text-sm text-white transition hover:bg-forest/90 disabled:opacity-50"
                  disabled={busy || !feedback.trim()}
                  onClick={advance}
                >
                  {busy ? "Rethinking…" : "Refine with this"}
                </button>
                <button
                  className="rounded-lg border border-forest bg-forest/5 px-4 py-2 text-sm text-forest transition hover:bg-forest/10 disabled:opacity-50"
                  disabled={busy}
                  onClick={lockAndCreate}
                  title="Lock this strategy and draft your first content from it"
                >
                  Lock it → draft my first content
                </button>
                {busy && handoffStage < 0 && <ThinkingStrip step={thinkStep} />}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border border-forest/30 bg-forest/5 p-5">
                <p className="text-sm text-ink">
                  ✓ Strategy locked after {session.turn_count} turn
                  {session.turn_count === 1 ? "" : "s"} — and here&apos;s your first content,
                  drafted straight from it.
                </p>
              </div>
              {content && (
                <div className="surface p-5">
                  <div className="flex items-center justify-between gap-3">
                    <p className="tlabel">
                      First content · {firstPosts.length} draft
                      {firstPosts.length === 1 ? "" : "s"}
                    </p>
                    {onOpenContent && (
                      <button
                        className="btn-line px-3 py-1.5 text-xs"
                        onClick={() => onOpenContent(content)}
                      >
                        Open in workspace →
                      </button>
                    )}
                  </div>
                  <div className="mt-3 space-y-3">
                    {firstPosts.map((t) => {
                      const o = t.output ?? {};
                      return (
                        <PlatformCard
                          key={t.id}
                          brand={brandName}
                          channel={String(o.channel ?? t.title)}
                          title={o.title ? String(o.title) : ""}
                          body={String(o.content ?? "")}
                          cta={o.call_to_action ? String(o.call_to_action) : ""}
                        />
                      );
                    })}
                  </div>
                  <p className="mt-3 text-xs text-ink/50">
                    These are drafts to react to — open the workspace to edit, review, or
                    schedule them.
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
