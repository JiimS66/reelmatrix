"use client";

import { useEffect, useState } from "react";

import { getInsights, learnInsights, type GrowthInsights } from "@/lib/teamApi";

import { RankedBarChart } from "./charts";

const TYPE_LABEL: Record<string, string> = {
  hook_type: "Hook",
  cta_style: "CTA",
  length_bucket: "Length",
};

/** The effect flywheel made visible: what's converting (learned from published
 * outcomes), the same priors the agents now generate from. */
export function GrowthInsightsCard({
  memberId,
  canLearn,
}: {
  memberId: string;
  canLearn: boolean;
}) {
  const [data, setData] = useState<GrowthInsights | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getInsights(memberId)
      .then(setData)
      .catch(() => setData(null));
  }, [memberId]);

  async function learn() {
    setBusy(true);
    try {
      setData(await learnInsights(memberId));
    } catch {
      /* surfaced elsewhere; keep the card quiet */
    } finally {
      setBusy(false);
    }
  }

  const byType: Record<string, GrowthInsights["attributes"]> = {};
  for (const a of data?.attributes ?? []) (byType[a.attribute_type] ||= []).push(a);

  return (
    <div className="surface p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="tlabel">What&apos;s working — the effect flywheel</p>
          <p className="mt-0.5 text-sm text-ink/55">
            Learned from published outcomes; fed back into every new draft.
          </p>
        </div>
        {canLearn && (
          <button
            className="btn-line shrink-0 px-2.5 py-1 text-xs"
            disabled={busy}
            onClick={learn}
          >
            {busy ? "Learning…" : "Learn from results ↻"}
          </button>
        )}
      </div>

      {data && data.priors.length > 0 ? (
        <ul className="mt-3 space-y-1">
          {data.priors.map((p, i) => (
            <li key={i} className="text-sm text-ink/80">
              — {p}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-ink/50">
          Not enough published outcomes yet — publish &amp; sync, then learn.
        </p>
      )}

      {data && data.attributes.length > 0 && (
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {Object.entries(byType).map(([type, rows]) => (
            <div key={type}>
              <p className="tlabel">{TYPE_LABEL[type] ?? type}</p>
              <div className="mt-1">
                <RankedBarChart
                  data={rows.map((r) => ({ label: r.attribute_value, "CVR": r.cvr }))}
                  labelKey="label"
                  valueKey="CVR"
                  unit="%"
                  labelWidth={68}
                  height={Math.max(56, rows.length * 30)}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
