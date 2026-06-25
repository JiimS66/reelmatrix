"use client";

import { useState } from "react";

import {
  advanceStrategySession,
  startStrategySession,
  type StrategySession,
} from "@/lib/teamApi";

/** Circuit A — the strategy co-creation loop, made tangible. The marketer feeds whatever
 * they have; the advisor makes its best guess, FLAGS what it's unsure of (confidence +
 * assumptions), and they sharpen it turn by turn. The point is to RECOGNIZE the right
 * strategy (react to options) rather than invent it — and to feel the loop: react → it
 * re-thinks → the draft sharpens, guesses turn into confirmations. (Phase 1: text input;
 * URL/file ingest is phase 2. "Lock it" will feed circuit B — content — next.) */

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

export function StrategyAdvisorPanel({ memberId }: { memberId: string }) {
  const [idea, setIdea] = useState("");
  const [session, setSession] = useState<StrategySession | null>(null);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const draft = session?.draft ?? null;

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
  const finish = () =>
    session && run(() => advanceStrategySession(memberId, session.id, { done: true }));

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
        <div className="mt-3 flex items-center gap-3">
          {!session ? (
            <button
              className="rounded-lg bg-forest px-4 py-2 text-sm text-white transition hover:bg-forest/90 disabled:opacity-50"
              disabled={busy || !idea.trim()}
              onClick={start}
            >
              {busy ? "Thinking…" : "Think it through"}
            </button>
          ) : (
            <>
              <span className="font-mono text-xs text-ink/45">
                turn {session.turn_count} · {session.status}
              </span>
              <button
                className="btn-line px-3 py-1.5 text-xs"
                onClick={() => {
                  setSession(null);
                  setIdea("");
                }}
              >
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
          <div className="surface border-l-2 border-forest p-5">
            <p className="tlabel">What I heard</p>
            <p className="mt-1 text-[15px] leading-relaxed text-ink">{draft.understanding}</p>
          </div>

          {/* Assumptions — the guesses it flagged, so the loop never stalls on missing info */}
          {draft.assumptions.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
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
          <div className="surface p-5">
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
          <div className="surface p-5">
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
          <div className="grid gap-5 sm:grid-cols-2">
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
          <div className="surface p-5">
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

          {/* The loop — react and iterate, or lock it */}
          {session?.status !== "done" ? (
            <div className="surface border border-forest/30 p-5">
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
                  className="btn-line px-3 py-2 text-xs"
                  disabled={busy}
                  onClick={finish}
                  title="Lock this strategy — next: generate content from it"
                >
                  Good enough — lock it
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-forest/30 bg-forest/5 p-5">
              <p className="text-sm text-ink">
                ✓ Strategy locked after {session.turn_count} turn
                {session.turn_count === 1 ? "" : "s"}.{" "}
                <span className="text-ink/55">
                  Next (phase 2): generate your first content straight from this.
                </span>
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
