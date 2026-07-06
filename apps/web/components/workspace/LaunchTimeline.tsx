"use client";

import { useEffect, useMemo, useState } from "react";

import {
  listExternalLinks,
  syncCampaignToLinear,
  type ExternalLink,
  type ScheduleData,
  type Task,
  type TaskStatus,
} from "@/lib/teamApi";

/** The campaign hero view: the launch schedule as channel swimlanes on a date
 * axis. Same-day posts cluster into one node (no overlap), phases render as a
 * tinted band instead of colliding labels, statuses are a clickable legend
 * (click = spotlight that status), and every node carries a hover card. Once
 * synced, nodes link through to their Linear issues. */

const STATUS_META: Record<TaskStatus, { dot: string; label: string }> = {
  done: { dot: "bg-emerald-500", label: "approved" },
  needs_review: { dot: "bg-amber-500", label: "in review" },
  in_progress: { dot: "bg-amber-300", label: "in progress" },
  blocked: { dot: "bg-red-500", label: "blocked" },
  todo: { dot: "bg-slate-300", label: "todo" },
};

// One accent only: phases are an opacity ramp of forest, peaking at launch.
const PHASE_TINT: Record<string, number> = {
  warmup: 0.06,
  buildup: 0.1,
  prelaunch: 0.16,
  launch: 0.28,
  followup: 0.08,
};

type DatedTask = Task & { due_date: string };

interface Hover {
  x: number;
  y: number;
  tasks: DatedTask[];
}

function dayIndex(date: string): number {
  return Math.floor(new Date(`${date}T00:00:00Z`).getTime() / 86_400_000);
}

function shortDate(date: string): string {
  const d = new Date(`${date}T00:00:00Z`);
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
}

export function LaunchTimeline({
  schedule,
  memberId,
  canSync,
  onSelectTask,
}: {
  schedule: ScheduleData;
  memberId: string;
  canSync: boolean;
  onSelectTask: (id: string) => void;
}) {
  const [links, setLinks] = useState<ExternalLink[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [syncOpen, setSyncOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncNote, setSyncNote] = useState<string | null>(null);
  const [spotlight, setSpotlight] = useState<TaskStatus | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);

  useEffect(() => {
    listExternalLinks(memberId, schedule.campaign.id)
      .then(setLinks)
      .catch(() => {});
  }, [memberId, schedule.campaign.id]);

  const dated = useMemo(
    () =>
      schedule.tasks.filter(
        (t): t is DatedTask =>
          !!t.due_date && (t.kind === "asset" || t.kind === "claim_check"),
      ),
    [schedule.tasks],
  );

  // lane → day → cluster of tasks (same-day posts become ONE node).
  const lanes = useMemo(() => {
    const byChannel = new Map<string, Map<string, DatedTask[]>>();
    for (const t of dated) {
      const channel =
        String(t.params?.channel ?? "") || (t.kind === "claim_check" ? "Review" : "Other");
      const days = byChannel.get(channel) ?? new Map<string, DatedTask[]>();
      const cluster = days.get(t.due_date) ?? [];
      cluster.push(t);
      days.set(t.due_date, cluster);
      byChannel.set(channel, days);
    }
    return [...byChannel.entries()].map(([channel, days]) => ({
      channel,
      clusters: [...days.entries()].map(([date, tasks]) => ({ date, tasks })),
    }));
  }, [dated]);

  const range = useMemo(() => {
    const days = [
      ...dated.map((t) => dayIndex(t.due_date)),
      ...schedule.milestones.map((m) => dayIndex(m.date)),
      ...(schedule.campaign.event_date ? [dayIndex(schedule.campaign.event_date)] : []),
    ];
    if (days.length === 0) return null;
    const min = Math.min(...days);
    const max = Math.max(...days);
    return { min, max, span: Math.max(max - min, 1) };
  }, [dated, schedule.milestones, schedule.campaign.event_date]);

  // Phase band segments: milestone i runs until milestone i+1 (or the end).
  const phaseSegments = useMemo(() => {
    if (!range) return [];
    const sorted = [...schedule.milestones].sort((a, b) => a.date.localeCompare(b.date));
    return sorted.map((m, i) => {
      const startPct = ((dayIndex(m.date) - range.min) / range.span) * 100;
      const end =
        i + 1 < sorted.length ? dayIndex(sorted[i + 1].date) : range.max + 1;
      const endPct = Math.min(((end - range.min) / range.span) * 100, 100);
      return {
        key: m.id,
        phase: m.phase,
        name: m.name,
        date: m.date,
        left: startPct,
        width: Math.max(endPct - startPct, 1),
      };
    });
  }, [schedule.milestones, range]);

  const statusCounts = useMemo(() => {
    const counts = new Map<TaskStatus, number>();
    for (const t of dated) counts.set(t.status, (counts.get(t.status) ?? 0) + 1);
    return counts;
  }, [dated]);

  if (!range || lanes.length === 0) return null;

  const pct = (date: string) => ((dayIndex(date) - range.min) / range.span) * 100;
  const clamp = (v: number) => Math.min(Math.max(v, 2), 98);
  const linkFor = (taskId: string) =>
    links.find((l) => l.local_kind === "task" && l.local_id === taskId);
  const projectLink = links.find((l) => l.local_kind === "campaign");

  async function refreshLinks() {
    try {
      setLinks(await listExternalLinks(memberId, schedule.campaign.id));
    } catch {
      /* links are decoration — never break the timeline */
    }
  }

  async function runSync() {
    if (!apiKey.trim()) return;
    setSyncing(true);
    setSyncNote(null);
    try {
      const result = await syncCampaignToLinear(memberId, {
        campaign_id: schedule.campaign.id,
        api_key: apiKey.trim(),
      });
      setSyncNote(result.detail);
      await refreshLinks();
    } catch (e) {
      setSyncNote(e instanceof Error ? e.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="surface relative p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-baseline gap-3">
          <p className="tlabel">Launch timeline</p>
          <p className="font-mono text-[11px] text-ink/45">
            {shortDate(schedule.milestones[0]?.date ?? dated[0]?.due_date ?? "")} →{" "}
            {schedule.campaign.event_date ? shortDate(schedule.campaign.event_date) : "rolling"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {projectLink?.url && (
            <a href={projectLink.url} target="_blank" rel="noreferrer" className="chip text-forest">
              Linear ↗
            </a>
          )}
          {canSync && (
            <button className="btn-line px-2.5 py-1 text-xs" onClick={() => setSyncOpen((v) => !v)}>
              Sync to Linear
            </button>
          )}
        </div>
      </div>

      {syncOpen && (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg bg-ink/[0.04] p-3">
          <input
            className="field min-w-56 flex-1 py-1.5 text-xs"
            type="password"
            placeholder="Linear API key — used once, never stored"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <button
            className="btn-dark px-3 py-1.5 text-xs"
            disabled={syncing || !apiKey.trim()}
            onClick={runSync}
          >
            {syncing ? "Syncing…" : "Push timeline"}
          </button>
          <p className="w-full font-mono text-[11px] text-ink/50">
            Project + one issue per dated task. Re-sync updates, never duplicates.
          </p>
          {syncNote && <p className="w-full text-xs text-forest">{syncNote}</p>}
        </div>
      )}

      {/* Clickable legend — click a status to spotlight it on the map. */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {(Object.keys(STATUS_META) as TaskStatus[])
          .filter((s) => (statusCounts.get(s) ?? 0) > 0)
          .map((s) => (
            <button
              key={s}
              onClick={() => setSpotlight((prev) => (prev === s ? null : s))}
              className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] transition ${
                spotlight === s
                  ? "border-ink bg-ink text-white"
                  : "border-ink/15 text-ink/60 hover:border-ink/40"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${STATUS_META[s].dot}`} />
              {STATUS_META[s].label} · {statusCounts.get(s)}
            </button>
          ))}
        {spotlight && (
          <button
            className="font-mono text-[11px] text-ink/40 underline hover:text-ink"
            onClick={() => setSpotlight(null)}
          >
            clear
          </button>
        )}
      </div>

      <div className="mt-3 space-y-2.5">
        {/* Phase band: tinted segments instead of colliding labels. */}
        <div className="flex items-center gap-3">
          <p className="w-28 shrink-0 font-mono text-[11px] text-ink/40">phase</p>
          <div className="relative flex h-6 flex-1 overflow-hidden rounded-md">
            {phaseSegments.map((seg) => (
              <div
                key={seg.key}
                className="group absolute top-0 flex h-full items-center justify-center overflow-hidden"
                style={{
                  left: `${seg.left}%`,
                  width: `${seg.width}%`,
                  backgroundColor: `rgba(63,110,31,${PHASE_TINT[seg.phase] ?? 0.1})`,
                }}
                title={`${seg.name} · from ${seg.date}`}
              >
                {seg.width > 9 && (
                  <span className="truncate px-1 font-mono text-[11px] text-ink/60">
                    {seg.phase}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {lanes.map(({ channel, clusters }) => (
          <div key={channel} className="flex items-center gap-3">
            <p className="w-28 shrink-0 truncate font-mono text-[11px] text-ink/60" title={channel}>
              {channel}
            </p>
            <div className="relative h-9 flex-1 rounded-full bg-ink/[0.04]">
              {schedule.campaign.event_date && (
                <div
                  className="absolute top-0 h-full w-px bg-forest/60"
                  style={{ left: `${clamp(pct(schedule.campaign.event_date))}%` }}
                />
              )}
              {clusters.map(({ date, tasks }) => {
                const lead = tasks[0];
                const dimmed = spotlight !== null && !tasks.some((t) => t.status === spotlight);
                const external = tasks.some((t) => linkFor(t.id));
                return (
                  <button
                    key={`${channel}-${date}`}
                    onClick={() => onSelectTask(lead.id)}
                    onMouseEnter={(e) => {
                      const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
                      const host = (e.currentTarget as HTMLElement)
                        .closest(".surface")!
                        .getBoundingClientRect();
                      setHover({ x: r.left - host.left + r.width / 2, y: r.top - host.top, tasks });
                    }}
                    onMouseLeave={() => setHover(null)}
                    className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 transition ${
                      dimmed ? "opacity-20" : "hover:scale-110"
                    }`}
                    style={{ left: `${clamp(pct(date))}%` }}
                  >
                    <span
                      className={`flex h-5 min-w-5 items-center justify-center rounded-full border-2 border-white px-0.5 shadow-soft ${STATUS_META[lead.status].dot}`}
                    >
                      {tasks.length > 1 && (
                        <span className="font-mono text-[11px] font-semibold text-white">
                          {tasks.length}
                        </span>
                      )}
                    </span>
                    {external && (
                      <span className="absolute -right-2 -top-2 text-[11px] text-forest">↗</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* Date axis: just the ends + the event flag. */}
        <div className="flex items-center gap-3">
          <p className="w-28 shrink-0" />
          <div className="relative h-4 flex-1 font-mono text-[11px] text-ink/40">
            <span className="absolute left-0">{shortDate(schedule.milestones[0]?.date ?? dated[0]?.due_date ?? "")}</span>
            {schedule.campaign.event_date && (
              <span
                className="absolute -translate-x-1/2 font-semibold text-forest"
                style={{ left: `${clamp(pct(schedule.campaign.event_date))}%` }}
              >
                ⚑ {shortDate(schedule.campaign.event_date)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Hover card — richer than a native tooltip, follows the cluster. */}
      {hover && (
        <div
          className="pointer-events-none absolute z-20 w-56 -translate-x-1/2 -translate-y-full rounded-lg border border-ink/10 bg-white p-2.5 shadow-soft"
          style={{ left: hover.x, top: hover.y - 6 }}
        >
          {hover.tasks.map((t) => (
            <div key={t.id} className="flex items-start gap-1.5 py-0.5">
              <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${STATUS_META[t.status].dot}`} />
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-ink">{t.title}</p>
                <p className="font-mono text-[11px] text-ink/45">
                  {t.due_date} · {STATUS_META[t.status].label}
                  {linkFor(t.id) ? " · in Linear ↗" : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
