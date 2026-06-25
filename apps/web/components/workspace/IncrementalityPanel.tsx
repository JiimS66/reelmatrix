"use client";

import { useState } from "react";

import { runIncrementality, type IncrementalityRow } from "@/lib/teamApi";

/** Phase 11 — causal de-bias: measure incremental lift and shrink attributes that just
 * rode high-intent traffic (correlation, not causation). */
export function IncrementalityPanel({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [tests, setTests] = useState<IncrementalityRow[] | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canManage) return null;

  async function run() {
    setBusy(true);
    try {
      setTests((await runIncrementality(memberId)).tests);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="tlabel">Causal de-bias — correlation → causation</p>
          <p className="mt-0.5 text-sm text-ink/55">
            Measures incremental lift; shrinks attributes that just rode high-intent
            traffic.
          </p>
        </div>
        <button
          className="btn-line shrink-0 px-2.5 py-1 text-xs"
          disabled={busy}
          onClick={run}
        >
          {busy ? "Measuring…" : "Measure causal lift"}
        </button>
      </div>
      {tests && tests.length > 0 && (
        <ul className="mt-3 space-y-1">
          {tests.map((t, i) => (
            <li key={i} className="flex items-center gap-2 text-[12px]">
              <span className="flex-1 truncate text-ink/70">
                {t.attribute_value}{" "}
                <span className="text-ink/40">({t.attribute_type})</span>
              </span>
              <span className="font-mono text-ink/45">
                {t.naive_conversions}→{t.incremental_conversions}
              </span>
              <span
                className={`w-12 text-right font-mono ${
                  t.multiplier < 1 ? "text-coral" : "text-forest"
                }`}
              >
                ×{t.multiplier}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
