"use client";

import { useEffect, useState } from "react";

import { getUsage, type UsageSummary } from "@/lib/teamApi";

/** Cost transparency: AI runs + tokens per employee, so "what does this team
 * cost to run" is answerable in one glance. Token pricing belongs to the
 * provider; we show volume and let the note carry the unit economics. */
export function UsageCard({ memberId }: { memberId: string }) {
  const [usage, setUsage] = useState<UsageSummary | null>(null);

  useEffect(() => {
    getUsage(memberId)
      .then(setUsage)
      .catch(() => {});
  }, [memberId]);

  if (!usage || usage.total_runs === 0) return null;

  return (
    <div className="surface p-5">
      <div className="flex items-baseline justify-between gap-2">
        <p className="tlabel">AI usage</p>
        <p className="font-mono text-[11px] text-ink/45">
          {usage.total_runs.toLocaleString()} runs
          {usage.total_tokens > 0 &&
            ` · ${usage.total_tokens.toLocaleString()} tokens`}
        </p>
      </div>
      <ul className="mt-3 space-y-1.5">
        {usage.rows.map((row) => {
          const share = usage.total_runs > 0 ? row.runs / usage.total_runs : 0;
          return (
            <li key={row.member_id} className="flex items-center gap-3">
              <p className="w-32 shrink-0 truncate text-sm text-ink" title={row.display_name}>
                {row.display_name}
              </p>
              <div className="h-2.5 flex-1 rounded-full bg-ink/[0.05]">
                <div
                  className="h-2.5 rounded-full bg-forest/70"
                  style={{ width: `${Math.max(share * 100, 2)}%` }}
                />
              </div>
              <p className="w-28 shrink-0 text-right font-mono text-[11px] text-ink/55">
                {row.runs} runs
                {row.providers.length > 0 && ` · ${row.providers.join("/")}`}
              </p>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 font-mono text-[11px] text-ink/40">
        Open-weight API rates make a full post ≈ a fraction of a cent — your
        team&apos;s review time is the real cost.
      </p>
    </div>
  );
}
