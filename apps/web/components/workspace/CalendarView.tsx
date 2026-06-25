"use client";

import { useState } from "react";

import type { Member, ScheduleData, Task, TrendAngle } from "@/lib/teamApi";

import { KIND_LABEL, StatusBadge } from "./primitives";

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function CalendarView({
  schedule,
  members,
  onSelectTask,
  canRefresh = false,
  onRefreshTrends,
  angles,
  onDraftAngle,
}: {
  schedule: ScheduleData;
  members: Member[];
  onSelectTask: (id: string) => void;
  canRefresh?: boolean;
  onRefreshTrends?: () => Promise<void> | void;
  angles?: TrendAngle[];
  onDraftAngle?: (angle: string, channel: string) => Promise<void> | void;
}) {
  const [refreshing, setRefreshing] = useState(false);
  const [drafting, setDrafting] = useState<string | null>(null);
  async function refresh() {
    if (!onRefreshTrends) return;
    setRefreshing(true);
    try {
      await onRefreshTrends();
    } finally {
      setRefreshing(false);
    }
  }
  async function draft(angle: string) {
    if (!onDraftAngle) return;
    setDrafting(angle);
    try {
      await onDraftAngle(angle, "X / Twitter");
    } finally {
      setDrafting(null);
    }
  }

  const tasksByPhase: Record<string, Task[]> = {};
  for (const task of schedule.tasks) {
    const phase = task.phase ?? "prep";
    (tasksByPhase[phase] ||= []).push(task);
  }
  const prepTasks = tasksByPhase["prep"] ?? [];

  return (
    <div className="space-y-5">
      <div className="surface p-5">
        <p className="tlabel">Event</p>
        <h2 className="mt-1 text-lg font-semibold text-ink">
          {schedule.campaign.event_name ?? schedule.campaign.name}
          {schedule.campaign.event_date && (
            <span className="ml-2 font-mono text-sm text-forest">
              {formatDate(schedule.campaign.event_date)}
            </span>
          )}
        </h2>
        <div className="mt-3">
          <div className="flex items-center justify-between gap-2">
            <p className="tlabel">Timely angles to ride</p>
            {canRefresh && onRefreshTrends && (
              <button
                className="btn-line px-2.5 py-1 text-xs"
                disabled={refreshing}
                onClick={refresh}
              >
                {refreshing ? "Pulling trends…" : "Refresh from trends ↻"}
              </button>
            )}
          </div>
          {angles && angles.length > 0 ? (
            <ul className="mt-1.5 space-y-1.5">
              {angles.map((a, i) => (
                <li
                  key={i}
                  className="flex items-start justify-between gap-2 rounded-lg border border-ink/10 bg-canvas px-2.5 py-1.5"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-ink/80">{a.angle}</p>
                    <p
                      className={`font-mono text-[10px] ${
                        a.safe ? "text-ink/45" : "text-red-600"
                      }`}
                    >
                      {a.safe ? `fit ${a.score} · ${a.reason}` : `⛔ ${a.reason}`}
                    </p>
                  </div>
                  {canRefresh && onDraftAngle && (
                    <button
                      className="btn-line shrink-0 px-2.5 py-1 text-xs disabled:opacity-40"
                      disabled={!a.safe || drafting !== null}
                      title={a.safe ? "Draft a rapid post" : "Blocked by brand-safety"}
                      onClick={() => draft(a.angle)}
                    >
                      {drafting === a.angle ? "Drafting…" : "Draft a rapid post"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          ) : schedule.timely_angles.length > 0 ? (
            <ul className="mt-1.5 space-y-1">
              {schedule.timely_angles.map((angle, i) => (
                <li key={i} className="text-sm text-ink/80">
                  — {angle}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1.5 text-sm text-ink/50">
              {canRefresh
                ? "Pull current hot topics to suggest timely hooks."
                : "No timely angles yet."}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {prepTasks.length > 0 && (
          <PhaseRow
            date={null}
            name="Prep"
            objective="Ideate and plan before warm-up"
            tasks={prepTasks}
            onSelectTask={onSelectTask}
          />
        )}
        {schedule.milestones.map((m) => (
          <PhaseRow
            key={m.id}
            date={m.date}
            name={m.name}
            objective={m.objective}
            tasks={tasksByPhase[m.phase] ?? []}
            onSelectTask={onSelectTask}
          />
        ))}
      </div>
    </div>
  );
}

function PhaseRow({
  date,
  name,
  objective,
  tasks,
  onSelectTask,
}: {
  date: string | null;
  name: string;
  objective: string;
  tasks: Task[];
  onSelectTask: (id: string) => void;
}) {
  return (
    <div className="surface p-4">
      <div className="flex items-baseline gap-3">
        <span className="w-16 shrink-0 font-mono text-[12px] text-forest">
          {date ? formatDate(date) : "—"}
        </span>
        <div>
          <h3 className="font-semibold text-ink">{name}</h3>
          <p className="text-sm text-ink/55">{objective}</p>
        </div>
      </div>
      {tasks.length > 0 && (
        <ul className="mt-3 space-y-1.5 sm:pl-[4.75rem]">
          {tasks.map((task) => (
            <li key={task.id}>
              <button
                onClick={() => onSelectTask(task.id)}
                className="flex w-full items-center gap-2 rounded-lg border border-ink/10 bg-white px-3 py-1.5 text-left text-sm hover:border-ink/25"
              >
                <span className="tlabel shrink-0">
                  {KIND_LABEL[task.kind] ?? task.kind}
                </span>
                <span className="flex-1 truncate text-ink">{task.title}</span>
                <StatusBadge status={task.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
