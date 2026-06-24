"use client";

import { useState } from "react";

import type { ScheduleData, Task } from "@/lib/teamApi";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const KIND_ABBR: Record<string, string> = {
  ideation: "Ideation",
  planning: "Plan",
  asset: "Asset",
  claim_check: "Claim",
};

function iso(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function MonthCalendar({
  schedule,
  onSelectTask,
}: {
  schedule: ScheduleData;
  onSelectTask: (id: string) => void;
}) {
  const seed = schedule.campaign.event_date ?? schedule.milestones[0]?.date ?? null;
  const seedDate = seed ? new Date(`${seed}T00:00:00`) : new Date();
  const [ym, setYm] = useState<{ y: number; m: number }>({
    y: seedDate.getFullYear(),
    m: seedDate.getMonth(),
  });

  const now = new Date();
  const todayIso = iso(now.getFullYear(), now.getMonth(), now.getDate());

  const tasksByDate: Record<string, Task[]> = {};
  for (const t of schedule.tasks) {
    if (t.due_date) (tasksByDate[t.due_date] ||= []).push(t);
  }
  const milestoneByDate: Record<string, string> = {};
  for (const ms of schedule.milestones) milestoneByDate[ms.date] = ms.name;

  const first = new Date(ym.y, ym.m, 1);
  const startWeekday = first.getDay();
  const daysInMonth = new Date(ym.y, ym.m + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  function shift(delta: number) {
    const n = new Date(ym.y, ym.m + delta, 1);
    setYm({ y: n.getFullYear(), m: n.getMonth() });
  }

  const monthLabel = first.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <button className="btn-line" onClick={() => shift(-1)} aria-label="Previous month">
          ‹
        </button>
        <h2 className="font-semibold text-ink">{monthLabel}</h2>
        <button className="btn-line" onClick={() => shift(1)} aria-label="Next month">
          ›
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1">
        {WEEKDAYS.map((w) => (
          <div
            key={w}
            className="pb-1 text-center font-mono text-[10px] text-ink/45"
          >
            {w}
          </div>
        ))}
        {cells.map((d, i) => {
          if (d === null) {
            return <div key={i} className="min-h-20 rounded-md bg-canvas/40" />;
          }
          const cellIso = iso(ym.y, ym.m, d);
          const isToday = cellIso === todayIso;
          const milestone = milestoneByDate[cellIso];
          const dayTasks = tasksByDate[cellIso] ?? [];
          return (
            <div
              key={i}
              className={`min-h-20 rounded-md border p-1 ${
                isToday ? "border-forest bg-forest/5" : "border-ink/10 bg-white"
              }`}
            >
              <div className="flex items-center justify-between gap-1">
                <span
                  className={`font-mono text-[11px] ${
                    isToday ? "font-bold text-forest" : "text-ink/50"
                  }`}
                >
                  {d}
                </span>
                {milestone && (
                  <span
                    className="truncate rounded-sm bg-forest/15 px-1 text-[9px] text-forest"
                    title={milestone}
                  >
                    {milestone}
                  </span>
                )}
              </div>
              <div className="mt-0.5 space-y-0.5">
                {dayTasks.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => onSelectTask(t.id)}
                    title={t.title}
                    className={`block w-full truncate rounded px-1 py-0.5 text-left text-[10px] ${
                      t.status === "done"
                        ? "bg-emerald-50 text-emerald-800"
                        : t.status === "needs_review"
                          ? "bg-amber-100 text-amber-900"
                          : "bg-canvas text-ink/70"
                    }`}
                  >
                    {KIND_ABBR[t.kind] ?? t.kind}: {t.title}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
