"use client";

import type { Member, TodoItem } from "@/lib/teamApi";

import { AssigneeChip, KIND_LABEL, StatusBadge } from "./primitives";

function parseDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatDate(iso: string): string {
  return parseDate(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function daysUntil(iso: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((parseDate(iso).getTime() - today.getTime()) / 86_400_000);
}

export function TodoView({
  items,
  members,
  onSelectTask,
}: {
  items: TodoItem[];
  members: Member[];
  onSelectTask: (id: string) => void;
}) {
  if (items.length === 0) {
    return (
      <p className="surface p-6 text-sm text-ink/60">
        No scheduled to-dos. Create a campaign with an event date to back-plan a
        timeline.
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {items.map(({ campaign_name, task }) => {
        const due = task.due_date ? daysUntil(task.due_date) : null;
        const overdue = due !== null && due < 0;
        return (
          <li key={task.id}>
            <button
              onClick={() => onSelectTask(task.id)}
              className="flex w-full items-center gap-3 rounded-2xl border border-ink/10 bg-white p-3.5 text-left hover:border-ink/25"
            >
              <div className="w-20 shrink-0">
                <div className="font-mono text-[12px] text-forest">
                  {task.due_date ? formatDate(task.due_date) : "—"}
                </div>
                {due !== null && (
                  <div
                    className={`font-mono text-[10px] ${
                      overdue ? "text-red-600" : "text-ink/45"
                    }`}
                  >
                    {overdue
                      ? `${-due}d overdue`
                      : due === 0
                        ? "today"
                        : `in ${due}d`}
                  </div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="tlabel shrink-0">
                    {KIND_LABEL[task.kind] ?? task.kind}
                  </span>
                  <span className="truncate font-semibold text-ink">
                    {task.title}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[11px] text-ink/45">
                    {campaign_name}
                  </span>
                  <AssigneeChip members={members} id={task.assignee_id} />
                </div>
              </div>
              <StatusBadge status={task.status} />
            </button>
          </li>
        );
      })}
    </ul>
  );
}
