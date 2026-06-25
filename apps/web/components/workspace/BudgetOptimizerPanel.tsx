"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { optimizeBudget, type BudgetPlan } from "@/lib/teamApi";

/** Phase 16 — global budget allocation across channels by marginal ROI (equimarginal
 * principle, mock response curves). Visualized with Recharts (Phase 15 dataviz). */
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
        <div className="mt-3">
          <ResponsiveContainer width="100%" height={150}>
            <BarChart
              data={plan.allocation}
              layout="vertical"
              margin={{ left: 8, right: 12, top: 4, bottom: 4 }}
            >
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="channel"
                width={92}
                tick={{ fontSize: 11, fill: "#10211b" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(63,110,31,0.06)" }}
                formatter={(value) => [`$${value}`, "allocated"]}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="allocated" fill="#3f6e1f" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
