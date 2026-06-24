"use client";

import type { ScheduleData, Task } from "@/lib/teamApi";

import { KIND_LABEL, StatusBadge, statusAccent } from "./primitives";

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${iso}T00:00:00`);
  const days = Math.round((target.getTime() - today.getTime()) / 86_400_000);
  return Number.isNaN(days) ? null : days;
}

function channelOf(task: Task): string {
  const c = task.params?.channel;
  return typeof c === "string" ? c : "";
}

export function UpcomingPanel({
  schedule,
  onSelectTask,
}: {
  schedule: ScheduleData;
  onSelectTask: (id: string) => void;
}) {
  const byPhase: Record<string, Task[]> = {};
  for (const t of schedule.tasks) (byPhase[t.phase ?? "prep"] ||= []).push(t);

  const phases: { key: string; name: string; date: string | null; objective: string }[] =
    [];
  if (byPhase["prep"]?.length) {
    phases.push({ key: "prep", name: "Prep", date: null, objective: "Ideate & plan" });
  }
  for (const m of schedule.milestones) {
    phases.push({ key: m.phase, name: m.name, date: m.date, objective: m.objective });
  }

  return (
    <div className="surface p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="tlabel">Upcoming</p>
        {schedule.campaign.event_date && (
          <span className="font-mono text-[11px] text-forest">
            launch {fmtDate(schedule.campaign.event_date)}
          </span>
        )}
      </div>
      <ol className="space-y-3">
        {phases.map((phase) => {
          const tasks = byPhase[phase.key] ?? [];
          const days = daysUntil(phase.date);
          const isPast = days !== null && days < 0;
          return (
            <li key={phase.key} className="flex gap-3">
              <div className="w-14 shrink-0 pt-0.5">
                <p
                  className={`font-mono text-[12px] ${
                    isPast ? "text-ink/35" : "text-forest"
                  }`}
                >
                  {phase.date ? fmtDate(phase.date) : "—"}
                </p>
                {days !== null && days >= 0 && (
                  <p className="font-mono text-[10px] text-ink/40">in {days}d</p>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{phase.name}</p>
                <p className="text-[12px] leading-5 text-ink/50">{phase.objective}</p>
                {tasks.length > 0 && (
                  <ul className="mt-1.5 space-y-1">
                    {tasks.map((task) => (
                      <li key={task.id} className="group relative">
                        <button
                          onClick={() => onSelectTask(task.id)}
                          className={`flex w-full items-center gap-2 rounded-md border-l-2 ${statusAccent(
                            task.status,
                          )} bg-canvas px-2 py-1 text-left text-[13px] hover:bg-white`}
                        >
                          <span className="tlabel shrink-0">
                            {KIND_LABEL[task.kind] ?? task.kind}
                          </span>
                          <span className="flex-1 truncate text-ink">{task.title}</span>
                        </button>
                        <div className="pointer-events-none absolute left-0 top-full z-10 mt-1 hidden w-64 rounded-lg border border-ink/10 bg-white p-3 shadow-soft group-hover:block">
                          <div className="flex items-center justify-between gap-2">
                            <span className="tlabel">
                              {KIND_LABEL[task.kind] ?? task.kind}
                            </span>
                            <StatusBadge status={task.status} />
                          </div>
                          <p className="mt-1 text-sm font-semibold text-ink">
                            {task.title}
                          </p>
                          <p className="mt-1 font-mono text-[11px] text-ink/50">
                            {channelOf(task) ? `${channelOf(task)} · ` : ""}
                            {task.due_date ? `due ${fmtDate(task.due_date)}` : "no date"}
                          </p>
                          <p className="mt-1.5 text-[11px] text-forest">Click to open</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
