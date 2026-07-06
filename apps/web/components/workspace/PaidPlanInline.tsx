"use client";

import { useState } from "react";

import { planPaid, type PaidPlan } from "@/lib/teamApi";

/** Phase 10 — score paid creative variants pre-spend and allocate a (mock) budget toward
 * winners (the create→test→reallocate loop). */
export function PaidPlanInline({
  memberId,
  taskId,
}: {
  memberId: string;
  taskId: string;
}) {
  const [plan, setPlan] = useState<PaidPlan | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      setPlan(await planPaid(memberId, taskId));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-ink/10 bg-canvas/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="tlabel">Paid ads — score variants, allocate budget</p>
        <button className="btn-line px-2.5 py-1 text-xs" disabled={busy} onClick={run}>
          {busy ? "…" : "Plan paid"}
        </button>
      </div>
      {plan && (
        <ul className="mt-2 space-y-1">
          {plan.variants.map((v, i) => (
            <li key={i} className="flex items-center gap-2 text-[12px]">
              <span className="w-16 font-mono text-[11px] text-ink/45">{v.angle}</span>
              <span className="flex-1 truncate text-ink/70">{v.headline}</span>
              <span className="font-mono text-forest">{v.creative_score}</span>
              <span className="font-mono text-[11px] text-ink/45">
                ${v.allocated_budget}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
