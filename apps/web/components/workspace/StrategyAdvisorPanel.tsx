"use client";

import { useState } from "react";

import { draftStrategy, type StrategyDraft } from "@/lib/teamApi";

/** Strategy co-creation (MVP, first slice) — the entry point for SMB/mid-market marketers
 * who don't have a big-data foundation. The marketer types a fuzzy idea; the AI advisor
 * RESTATES what it heard, then OFFERS audience candidates + positioning angles to pick from
 * (marketers choose better than they fill forms), plus content pillars, a plain-language
 * measure, and follow-up questions. It should feel like thinking WITH a CMO.
 *
 * First slice: one pass; picks are local highlights and the multi-turn refine + real-LLM
 * reasoning is the next step. The only "data" this needs is an LLM — the lowest data bar
 * of any capability, which is the whole point. */
export function StrategyAdvisorPanel({ memberId }: { memberId: string }) {
  const [idea, setIdea] = useState("");
  const [draft, setDraft] = useState<StrategyDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audiencePick, setAudiencePick] = useState<number | null>(null);
  const [anglePick, setAnglePick] = useState<number | null>(null);

  async function think() {
    if (!idea.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setDraft(await draftStrategy(memberId, idea.trim()));
      setAudiencePick(null);
      setAnglePick(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* The ask — a sentence, not a form */}
      <div className="surface p-6">
        <p className="tlabel">Strategy co-creation</p>
        <h2 className="mt-1 text-lg text-ink">Let&apos;s think your strategy through</h2>
        <p className="mt-1 max-w-2xl text-sm text-ink/60">
          Tell me what you want to take to market — a sentence is enough. I&apos;ll tidy it
          up, suggest who it&apos;s really for, and a few angles to react to. No form to fill.
        </p>
        <textarea
          className="mt-3 w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
          rows={3}
          placeholder="e.g. I built an AI tool that proofreads marketing copy for small teams…"
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            className="rounded-lg bg-forest px-4 py-2 text-sm text-white transition hover:bg-forest/90 disabled:opacity-50"
            disabled={busy || !idea.trim()}
            onClick={think}
          >
            {busy ? "Thinking…" : draft ? "Rethink" : "Think it through"}
          </button>
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>
      </div>

      {draft && (
        <>
          {/* Understanding — the warm restatement that makes them feel heard */}
          <div className="surface border-l-2 border-forest p-5">
            <p className="tlabel">What I heard</p>
            <p className="mt-1 text-[15px] leading-relaxed text-ink">{draft.understanding}</p>
          </div>

          {/* Audience candidates — offered to pick/react, never "everyone" */}
          <div className="surface p-5">
            <p className="tlabel">Who it&apos;s really for — pick the closest</p>
            <p className="mt-0.5 text-sm text-ink/55">
              Narrow beats &quot;everyone&quot;. Choose one, or tell me it&apos;s someone else.
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {draft.audience_candidates.map((a, i) => (
                <button
                  key={i}
                  onClick={() => setAudiencePick(i === audiencePick ? null : i)}
                  className={`rounded-lg border p-3 text-left transition ${
                    audiencePick === i
                      ? "border-forest bg-forest/10"
                      : "border-ink/12 hover:border-ink/25"
                  }`}
                >
                  <p className="text-sm font-medium text-ink">{a.name}</p>
                  <p className="mt-1 text-xs text-ink/60">{a.why}</p>
                  <p className="mt-1.5 text-xs text-forest">Pain: {a.pain}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Positioning angles — pick/react */}
          <div className="surface p-5">
            <p className="tlabel">Angles to stand out — which feels like you?</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {draft.positioning_angles.map((a, i) => (
                <button
                  key={i}
                  onClick={() => setAnglePick(i === anglePick ? null : i)}
                  className={`rounded-lg border p-3 text-left transition ${
                    anglePick === i
                      ? "border-forest bg-forest/10"
                      : "border-ink/12 hover:border-ink/25"
                  }`}
                >
                  <p className="text-sm font-medium text-ink">{a.angle}</p>
                  <p className="mt-1 text-xs text-ink/60">{a.rationale}</p>
                </button>
              ))}
            </div>
          </div>

          {/* The rest of the one-pager: pillars · channels · measure */}
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

          {/* Next questions — the advisor keeps the conversation going (the brainstorm space) */}
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
            <p className="mt-3 text-xs text-ink/45">
              Next step (coming): answer these and I&apos;ll refine the strategy with you,
              turn by turn.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
