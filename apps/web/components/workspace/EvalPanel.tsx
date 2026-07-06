"use client";

import { useState } from "react";

import { runEvals, type EvalRunResult } from "@/lib/teamApi";

/** Phase 12 — LLMOps: the eval suite as a quality regression gate. Graders run the real
 * policy/GEO gates, so the score reflects actual behavior. */
export function EvalPanel({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [res, setRes] = useState<EvalRunResult | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canManage) return null;

  async function run() {
    setBusy(true);
    try {
      setRes(await runEvals(memberId));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="tlabel">Evals — quality regression gate</p>
          <p className="mt-0.5 text-sm text-ink/55">
            Graders run the real policy/GEO gates; the score gates agent changes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {res && (
            <span
              className={`rounded-full px-2 py-0.5 font-mono text-[11px] ${
                res.passed ? "bg-forest text-white" : "bg-coral/20 text-coral"
              }`}
            >
              {Math.round(res.overall * 100)}%
            </span>
          )}
          <button
            className="btn-line shrink-0 px-2.5 py-1 text-xs"
            disabled={busy}
            onClick={run}
          >
            {busy ? "Running…" : "Run evals"}
          </button>
        </div>
      </div>
      {res && (
        <ul className="mt-3 space-y-1">
          {res.cases.map((c, i) => (
            <li key={i} className="flex items-center gap-2 text-[12px]">
              <span className={c.passed ? "text-forest" : "text-coral"}>
                {c.passed ? "✓" : "✗"}
              </span>
              <span className="flex-1 truncate text-ink/70">{c.name}</span>
              <span className="font-mono text-[11px] text-ink/40">{c.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
