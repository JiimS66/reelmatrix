"use client";

import { useEffect, useState } from "react";

import {
  dismissCandidate,
  discoverSegments,
  draftWhitespace,
  getMarketIntel,
  getSegmentScorecard,
  promoteCandidate,
  type MarketIntel,
  type SegmentScorecard,
} from "@/lib/teamApi";

const STATUS_TONE: Record<string, string> = {
  validated: "bg-forest text-white",
  "on-track": "bg-ink/10 text-ink/60",
  underperforming: "bg-coral/20 text-coral",
  unproven: "border border-ink/15 text-ink/45",
};

/** Phase 6 — ICP as a tested result (validation status + drivers + discovery) and the
 * market context a brief should never be written without. */
export function IcpMarketPanel({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [card, setCard] = useState<SegmentScorecard | null>(null);
  const [market, setMarket] = useState<MarketIntel | null>(null);
  const [busy, setBusy] = useState(false);
  const [drafted, setDrafted] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getSegmentScorecard(memberId), getMarketIntel(memberId)])
      .then(([c, m]) => {
        setCard(c);
        setMarket(m);
      })
      .catch(() => {});
  }, [memberId]);

  async function act(fn: () => Promise<SegmentScorecard>) {
    setBusy(true);
    try {
      setCard(await fn());
    } finally {
      setBusy(false);
    }
  }

  async function draft(angle: string) {
    setBusy(true);
    try {
      await draftWhitespace(memberId, angle);
      setDrafted(angle);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="surface p-5">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="tlabel">ICP validation — segments as tested results</p>
            <p className="mt-0.5 text-sm text-ink/55">
              Scored from real conversions, not assumptions.
            </p>
          </div>
          {canManage && (
            <button
              className="btn-line shrink-0 px-2.5 py-1 text-xs"
              disabled={busy}
              onClick={() => act(() => discoverSegments(memberId))}
            >
              Discover segments
            </button>
          )}
        </div>
        <ul className="mt-3 space-y-1.5">
          {(card?.segments ?? []).map((s, i) => (
            <li key={i} className="flex items-center gap-2 text-sm">
              <span className="flex-1 truncate text-ink">{s.segment}</span>
              {s.drivers.length > 0 && (
                <span className="hidden font-mono text-[11px] text-ink/40 sm:inline">
                  {s.drivers.join(" · ")}
                </span>
              )}
              <span className="font-mono text-[11px] text-forest">{s.cvr}%</span>
              <span
                className={`rounded-full px-1.5 text-[11px] ${
                  STATUS_TONE[s.status] ?? ""
                }`}
              >
                {s.status}
              </span>
            </li>
          ))}
        </ul>
        {(card?.candidates ?? []).length > 0 && (
          <div className="mt-3 border-t border-ink/10 pt-3">
            <p className="tlabel">Discovered candidates</p>
            <ul className="mt-1.5 space-y-2">
              {card!.candidates.map((c) => (
                <li key={c.id} className="rounded-lg border border-ink/10 bg-canvas p-2.5">
                  <p className="text-sm text-ink">{c.name}</p>
                  <p className="mt-0.5 text-[12px] text-ink/55">{c.rationale}</p>
                  {canManage && (
                    <div className="mt-1.5 flex gap-2">
                      <button
                        className="btn-line px-2 py-0.5 text-[11px]"
                        disabled={busy}
                        onClick={() => act(() => promoteCandidate(memberId, c.id))}
                      >
                        Promote
                      </button>
                      <button
                        className="btn-line px-2 py-0.5 text-[11px]"
                        disabled={busy}
                        onClick={() => act(() => dismissCandidate(memberId, c.id))}
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {market && (
        <div className="surface p-5">
          <p className="tlabel">Market context — don&apos;t write in a vacuum</p>
          <div className="mt-3 grid gap-5 sm:grid-cols-2">
            <div>
              <p className="tlabel">Competitors</p>
              <ul className="mt-1 space-y-1.5">
                {market.competitors.map((c, i) => (
                  <li key={i} className="text-sm">
                    <span className="text-ink">{c.name}</span>
                    <span className="text-ink/55"> — {c.positioning}</span>
                    <span className="block text-[11px] text-forest/80">
                      ↳ {c.recent_change}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="tlabel mt-3">Share of voice</p>
              <ul className="mt-1 space-y-1">
                {Object.entries(market.share_of_voice).map(([k, v]) => (
                  <li key={k} className="flex items-center gap-2 text-[12px]">
                    <span className="w-24 truncate text-ink/70">{k}</span>
                    <span
                      className="h-1.5 rounded bg-forest"
                      style={{ width: `${v}%` }}
                    />
                    <span className="font-mono text-[11px] text-ink/45">{v}%</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="tlabel">Audience questions</p>
              <ul className="mt-1 space-y-1">
                {market.audience_questions.map((q, i) => (
                  <li key={i} className="text-[12px] text-ink/70">
                    — {q}
                  </li>
                ))}
              </ul>
              <p className="tlabel mt-3">Whitespace</p>
              <ul className="mt-1 space-y-1.5">
                {market.whitespace.map((w, i) => (
                  <li key={i} className="flex items-start justify-between gap-2">
                    <span className="text-[12px] text-ink/70">— {w}</span>
                    {canManage && (
                      <button
                        className="btn-line shrink-0 px-2 py-0.5 text-[11px]"
                        disabled={busy}
                        onClick={() => draft(w)}
                      >
                        {drafted === w ? "Drafted ✓" : "Draft"}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
