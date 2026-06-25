"use client";

import { useState } from "react";

import { optimizeBudget, type BudgetPlan } from "@/lib/teamApi";

/** Phase 16 — global budget allocation across channels by marginal ROI (equimarginal
 * principle, mock response curves). */
export function BudgetOptimizerPanel({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [plan, setPlan] = useState<BudgetPlan | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canManage) return null;

  async function run() {
    setBusy(true);
    try {
      setPlan(await optimizeBudget(memberId, 5000));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="tlabel">Budget — allocate by marginal ROI</p>
          <p className="mt-0.5 text-sm text-ink/55">
            Equimarginal split across channels (mock response curves; MMM later).
          </p>
        </div>
        <button
          className="btn-line shrink-0 px-2.5 py-1 text-xs"
          disabled={busy}
          onClick={run}
        >
          {busy ? "Optimizing…" : "Optimize $5k"}
        </button>
      </div>
      {plan && (
        <ul className="mt-3 space-y-1">
          {plan.allocation.map((r, i) => (
            <li key={i} className="flex items-center gap-2 text-[12px]">
              <span className="flex-1 truncate text-ink/70">{r.channel}</span>
              <span className="font-mono text-forest">${r.allocated}</span>
              <span className="w-20 text-right font-mono text-[10px] text-ink/40">
                mROI {r.marginal_roi}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
