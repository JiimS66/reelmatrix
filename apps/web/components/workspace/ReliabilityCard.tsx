"use client";

import { useEffect, useState } from "react";

import { getReliability, type ReliabilityRow } from "@/lib/teamApi";

const MODE_LABEL: Record<string, string> = {
  ai_auto: "AI auto",
  ai_draft_human_review: "AI draft + review",
  human_only: "Human only",
};
const MODE_TONE: Record<string, string> = {
  ai_auto: "bg-forest text-white",
  ai_draft_human_review: "bg-ink/10 text-ink/60",
  human_only: "border border-coral/40 text-coral",
};

/** Phase 9 — automation level should follow PROVEN reliability, not be a fixed setting.
 * Each AI employee's reliability + the autonomy it has earned. */
export function ReliabilityCard({ memberId }: { memberId: string }) {
  const [rows, setRows] = useState<ReliabilityRow[]>([]);

  useEffect(() => {
    getReliability(memberId)
      .then(setRows)
      .catch(() => {});
  }, [memberId]);

  if (rows.length === 0) return null;

  return (
    <div className="surface p-5">
      <p className="tlabel">Agent reliability — earned autonomy</p>
      <p className="mt-0.5 text-sm text-ink/55">
        Automation level should follow proven reliability, not be fixed.
      </p>
      <ul className="mt-3 space-y-1.5">
        {rows.map((r) => (
          <li key={r.member_id} className="flex items-center gap-2 text-sm">
            <span className="flex-1 truncate text-ink">{r.display_name}</span>
            <span className="font-mono text-[11px] text-ink/40">{r.runs} runs</span>
            <span className="font-mono text-[11px] text-forest">{r.reliability}</span>
            <span
              className={`rounded-full px-1.5 text-[11px] ${
                MODE_TONE[r.recommended_mode] ?? ""
              }`}
            >
              {MODE_LABEL[r.recommended_mode] ?? r.recommended_mode}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
