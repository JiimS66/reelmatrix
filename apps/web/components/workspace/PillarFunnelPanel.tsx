"use client";

import { useEffect, useState } from "react";

import {
  atomizePillar,
  createPillar,
  draftFunnelGap,
  draftShort,
  getClips,
  getFunnelCoverage,
  getPillars,
  type Clip,
  type FunnelCoverage,
  type Pillar,
} from "@/lib/teamApi";

/** Phase 7 — funnel × segment coverage (fill gaps) + pillar atomization (one source →
 * many linked channel posts). */
export function PillarFunnelPanel({
  memberId,
  campaignId,
  canManage,
  onChanged,
}: {
  memberId: string;
  campaignId: string;
  canManage: boolean;
  onChanged: () => void;
}) {
  const [cov, setCov] = useState<FunnelCoverage | null>(null);
  const [pillars, setPillars] = useState<Pillar[]>([]);
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [clips, setClips] = useState<{ pillarId: string; items: Clip[] } | null>(null);

  async function refresh() {
    try {
      const [c, p] = await Promise.all([
        getFunnelCoverage(memberId, campaignId),
        getPillars(memberId, campaignId),
      ]);
      setCov(c);
      setPillars(p);
    } catch {
      /* surfaced elsewhere */
    }
  }
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memberId, campaignId]);

  async function fillGap(funnel_stage: string, segment: string) {
    setBusy(true);
    try {
      setCov(await draftFunnelGap(memberId, campaignId, { funnel_stage, segment }));
      onChanged();
    } finally {
      setBusy(false);
    }
  }
  async function addPillar() {
    if (!title.trim()) return;
    setBusy(true);
    try {
      setPillars(
        await createPillar(memberId, campaignId, {
          title: title.trim(),
          source_text: source.trim(),
        }),
      );
      setTitle("");
      setSource("");
    } finally {
      setBusy(false);
    }
  }
  async function atomize(pid: string) {
    setBusy(true);
    try {
      await atomizePillar(memberId, pid, ["LinkedIn", "Email", "X / Twitter"]);
      await refresh();
      onChanged();
    } finally {
      setBusy(false);
    }
  }
  async function showClips(pid: string) {
    try {
      const c = await getClips(memberId, pid);
      setClips({ pillarId: pid, items: c.clips });
    } catch {
      /* surfaced elsewhere */
    }
  }
  async function draftFromClip(pid: string, hook: string) {
    setBusy(true);
    try {
      await draftShort(memberId, pid, hook);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  const maxCount = Math.max(
    1,
    ...(cov
      ? cov.stages.flatMap((st) => cov.segments.map((sg) => cov.matrix[st]?.[sg] ?? 0))
      : [0]),
  );

  return (
    <div className="space-y-5">
      {cov && (
        <div className="surface p-5">
          <p className="tlabel">Funnel coverage — every stage × segment</p>
          <p className="mt-0.5 text-sm text-ink/55">
            Empty cells are gaps; fill one with a drafted post.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="tlabel" />
                  {cov.segments.map((s) => (
                    <th key={s} className="tlabel px-2 text-left">
                      {s}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cov.stages.map((st) => (
                  <tr key={st}>
                    <td className="py-1 pr-2 font-mono text-[11px] text-forest">{st}</td>
                    {cov.segments.map((sg) => {
                      const n = cov.matrix[st]?.[sg] ?? 0;
                      return (
                        <td key={sg} className="px-1 py-1 text-center">
                          {n > 0 ? (
                            <span
                              className="inline-block min-w-7 rounded px-1.5 py-0.5 font-mono text-[12px]"
                              style={{
                                backgroundColor: `rgba(63,110,31,${0.15 + (n / maxCount) * 0.55})`,
                                color: n / maxCount > 0.6 ? "white" : "#10211b",
                              }}
                            >
                              {n}
                            </span>
                          ) : canManage ? (
                            <button
                              className="btn-line px-1.5 py-0.5 text-[10px]"
                              disabled={busy}
                              onClick={() => fillGap(st, sg)}
                            >
                              + draft
                            </button>
                          ) : (
                            <span className="text-coral">·</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="surface p-5">
        <p className="tlabel">Pillar content — atomize one source into many posts</p>
        {canManage && (
          <div className="mt-3 space-y-2">
            <input
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
              placeholder="Pillar title — e.g. State of AI testing 2026"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <textarea
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
              rows={2}
              placeholder="Source text / transcript…"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
            <button
              className="btn-line px-3 py-1.5 text-xs"
              disabled={busy || !title.trim()}
              onClick={addPillar}
            >
              Add pillar
            </button>
          </div>
        )}
        {pillars.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {pillars.map((p) => (
              <li
                key={p.id}
                className="rounded-lg border border-ink/10 bg-canvas px-3 py-1.5"
              >
                <div className="flex items-center gap-2 text-sm">
                  <span className="flex-1 truncate text-ink">{p.title}</span>
                  <span className="font-mono text-[10px] text-ink/45">
                    {p.derivatives} posts
                  </span>
                  <button
                    className="btn-line px-2 py-0.5 text-[11px]"
                    disabled={busy}
                    onClick={() => showClips(p.id)}
                  >
                    Clips
                  </button>
                  {canManage && (
                    <button
                      className="btn-line px-2 py-0.5 text-[11px]"
                      disabled={busy}
                      onClick={() => atomize(p.id)}
                    >
                      Atomize
                    </button>
                  )}
                </div>
                {clips?.pillarId === p.id && clips.items.length > 0 && (
                  <ul className="mt-2 space-y-1 border-t border-ink/10 pt-2">
                    {clips.items.map((c, i) => (
                      <li key={i} className="flex items-center gap-2 text-[12px]">
                        <span className="font-mono text-forest">{c.clip_score}</span>
                        <span
                          className="flex-1 truncate text-ink/70"
                          title={c.reason}
                        >
                          {c.hook_sentence}
                        </span>
                        {canManage && (
                          <button
                            className="btn-line px-1.5 py-0.5 text-[10px]"
                            disabled={busy}
                            onClick={() => draftFromClip(p.id, c.hook_sentence)}
                          >
                            Draft short
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
