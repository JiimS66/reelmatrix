"use client";

import { useEffect, useState } from "react";

import {
  decideExperiment,
  designExperiment,
  getExperiments,
  type Experiment,
} from "@/lib/teamApi";

import { RankedBarChart } from "./charts";

const STATUS_TONE: Record<string, string> = {
  winner: "bg-forest text-white",
  loser: "bg-ink/10 text-ink/45",
  inconclusive: "bg-ink/10 text-ink/60",
  control: "border border-ink/20 text-ink/60",
  untested: "border border-ink/15 text-ink/45",
};

/** Phase 5b — race attribute-tagged variants; each winner becomes a generation rule
 * the writers reuse (surfaced as an "Experiment-proven" prior in What's-working). */
export function ExperimentsPanel({
  memberId,
  campaignId,
  canManage,
}: {
  memberId: string;
  campaignId: string;
  canManage: boolean;
}) {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [hypothesis, setHypothesis] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setExperiments(await getExperiments(memberId, campaignId));
    } catch {
      /* surfaced elsewhere */
    }
  }
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memberId, campaignId]);

  async function design() {
    if (!hypothesis.trim()) return;
    setBusy(true);
    try {
      await designExperiment(memberId, campaignId, {
        hypothesis: hypothesis.trim(),
        n: 4,
      });
      setHypothesis("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function decide(id: string) {
    setBusy(true);
    try {
      await decideExperiment(memberId, id);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <p className="tlabel">Experiments — race tagged variants, promote the winner</p>
      <p className="mt-0.5 text-sm text-ink/55">
        Each winning attribute combo becomes a generation rule the writers reuse.
      </p>

      {canManage && (
        <div className="mt-3 flex gap-2">
          <input
            className="flex-1 rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
            placeholder="Hypothesis — e.g. a curiosity hook lifts signups"
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
          />
          <button
            className="btn-line shrink-0 px-3 py-1.5 text-xs"
            disabled={busy || !hypothesis.trim()}
            onClick={design}
          >
            Design variants
          </button>
        </div>
      )}

      {experiments.length === 0 ? (
        <p className="mt-3 text-sm text-ink/50">No experiments yet.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {experiments.map((exp) => (
            <li key={exp.id} className="rounded-lg border border-ink/10 bg-canvas p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-ink">{exp.hypothesis}</p>
                {canManage && exp.status === "running" ? (
                  <button
                    className="btn-line shrink-0 px-2.5 py-1 text-xs"
                    disabled={busy}
                    onClick={() => decide(exp.id)}
                  >
                    Run &amp; decide
                  </button>
                ) : (
                  <span className="shrink-0 font-mono text-[10px] text-ink/45">
                    {exp.status}
                  </span>
                )}
              </div>
              {exp.status === "decided" && (
                <div className="mt-2">
                  <RankedBarChart
                    data={exp.variants.map((v) => ({ label: v.key, "CVR": v.cvr }))}
                    labelKey="label"
                    valueKey="CVR"
                    unit="%"
                    labelWidth={28}
                    height={Math.max(56, exp.variants.length * 26)}
                  />
                </div>
              )}
              <ul className="mt-2 space-y-1">
                {exp.variants.map((v) => (
                  <li key={v.key} className="flex items-center gap-2 text-sm">
                    <span className="w-5 font-mono text-[11px] text-ink/50">
                      {v.key}
                    </span>
                    <span className="flex-1 truncate text-[12px] text-ink/70">
                      {Object.values(v.attributes).join(" · ")}
                    </span>
                    {exp.status === "decided" && (
                      <span className="font-mono text-[11px] text-forest">
                        {v.cvr}%
                      </span>
                    )}
                    {exp.status === "decided" && v.key !== "control" && (
                      <span className="font-mono text-[10px] text-ink/45">
                        p{v.chance_to_beat_control}
                      </span>
                    )}
                    <span
                      className={`rounded-full px-1.5 text-[10px] ${
                        STATUS_TONE[v.result_status] ?? ""
                      }`}
                    >
                      {v.result_status}
                    </span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
