"use client";

import type { Board, Member, ScheduleData, Task } from "@/lib/teamApi";

import { CalendarView } from "./CalendarView";
import {
  AssigneeChip,
  KIND_LABEL,
  StatusBadge,
  checkCount,
  dueInfo,
} from "./primitives";

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${iso}T00:00:00`);
  const days = Math.round((target.getTime() - today.getTime()) / 86_400_000);
  return Number.isNaN(days) ? null : days;
}

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

interface HomeViewProps {
  role: "lead" | "member";
  board: Board | null;
  schedule: ScheduleData | null;
  inbox: Task[];
  members: Member[];
  currentMemberId: string;
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onApprove: (id: string) => void;
  onBulkApprove: (ids: string[]) => void;
  onStart: () => void;
}

export function HomeView({
  role,
  board,
  schedule,
  inbox,
  members,
  currentMemberId,
  selectedId,
  busy,
  onSelect,
  onApprove,
  onBulkApprove,
  onStart,
}: HomeViewProps) {
  if (!board) {
    if (role !== "lead") {
      return (
        <p className="surface p-6 text-sm text-ink/60">
          No campaign yet. When the lead starts one, your tasks land here.
        </p>
      );
    }
    return (
      <div className="surface p-6">
        <p className="tlabel">Start</p>
        <h2 className="mt-1 text-lg font-semibold text-ink">Start a launch</h2>
        <p className="mt-1 max-w-md text-sm text-ink/60">
          Pick the event and let the AI team draft the whole package and lay out
          the schedule. You review, tweak, reassign, or take over any step after.
        </p>
        <button className="btn-dark mt-4" disabled={busy} onClick={onStart}>
          {busy ? "Drafting…" : "New TestSprite launch →"}
        </button>
      </div>
    );
  }

  const tasks = board.tasks;
  const isLead = role === "lead";

  const reviews = isLead ? tasks.filter((t) => t.status === "needs_review") : [];
  const cleanReviews = reviews.filter((t) => checkCount(t) === 0);

  const actionable = (isLead
    ? tasks.filter((t) => t.assignee_id === currentMemberId)
    : inbox
  ).filter((t) => t.status === "todo" || t.status === "in_progress");

  const overdue = actionable.filter((t) => (daysUntil(t.due_date) ?? 9999) < 0);
  const thisWeek = actionable.filter((t) => {
    const d = daysUntil(t.due_date);
    return d !== null && d >= 0 && d <= 7;
  });
  const later = actionable.filter((t) => (daysUntil(t.due_date) ?? -1) > 7);
  const nodate = actionable.filter((t) => daysUntil(t.due_date) === null);

  const eventDays = daysUntil(schedule?.campaign.event_date ?? null);
  const nextMilestone =
    schedule?.milestones.find((m) => (daysUntil(m.date) ?? -1) >= 0) ?? null;
  const done = tasks.filter((t) => t.status === "done").length;
  const queueCount =
    reviews.length + overdue.length + thisWeek.length + later.length + nodate.length;

  return (
    <div className="space-y-5">
      {/* Status strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="surface p-3">
          <p className="tlabel">Event</p>
          <p
            className="mt-0.5 truncate text-sm font-semibold text-forest"
            title={schedule?.campaign.event_name ?? board.campaign.name}
          >
            {schedule?.campaign.event_name ?? board.campaign.name}
          </p>
          <p className="font-mono text-[11px] text-ink/50">
            {eventDays === null
              ? "no date"
              : `${eventDays < 0 ? "Launched" : `In ${eventDays}d`}${
                  schedule?.campaign.event_date
                    ? ` · ${fmtDate(schedule.campaign.event_date)}`
                    : ""
                }`}
          </p>
        </div>
        <Stat
          label="Phase"
          value={nextMilestone ? nextMilestone.name : "Post-launch"}
          sub={nextMilestone ? fmtDate(nextMilestone.date) : "wrap-up"}
        />
        <Stat
          label="Needs you"
          value={String(queueCount)}
          sub={overdue.length > 0 ? `${overdue.length} overdue` : "on track"}
        />
        <Stat label="Progress" value={`${done}/${tasks.length}`} sub="tasks done" />
      </div>

      {/* Agenda */}
      {isLead && reviews.length > 0 && (
        <Section
          title={`To review · ${reviews.length}`}
          action={
            cleanReviews.length > 0 ? (
              <button
                className="btn-dark"
                disabled={busy}
                onClick={() => onBulkApprove(cleanReviews.map((t) => t.id))}
              >
                Approve all clean ({cleanReviews.length})
              </button>
            ) : null
          }
        >
          {reviews.map((t) => (
            <AgendaRow
              key={t.id}
              task={t}
              members={members}
              selected={t.id === selectedId}
              busy={busy}
              onSelect={() => onSelect(t.id)}
              onApprove={() => onApprove(t.id)}
            />
          ))}
        </Section>
      )}

      {overdue.length > 0 && (
        <Bucket
          title="Overdue"
          danger
          tasks={overdue}
          members={members}
          selectedId={selectedId}
          busy={busy}
          onSelect={onSelect}
        />
      )}
      {thisWeek.length > 0 && (
        <Bucket
          title="This week"
          tasks={thisWeek}
          members={members}
          selectedId={selectedId}
          busy={busy}
          onSelect={onSelect}
        />
      )}
      {later.length > 0 && (
        <Bucket
          title="Upcoming"
          tasks={later}
          members={members}
          selectedId={selectedId}
          busy={busy}
          onSelect={onSelect}
        />
      )}
      {nodate.length > 0 && (
        <Bucket
          title="No due date"
          tasks={nodate}
          members={members}
          selectedId={selectedId}
          busy={busy}
          onSelect={onSelect}
        />
      )}
      {queueCount === 0 && (
        <p className="surface p-4 text-sm text-ink/60">
          You&apos;re all caught up — nothing needs you right now.
        </p>
      )}

      {/* Calendar */}
      <div>
        <p className="tlabel mb-2">Schedule</p>
        {schedule ? (
          <CalendarView
            schedule={schedule}
            members={members}
            onSelectTask={onSelect}
          />
        ) : (
          <p className="surface p-4 text-sm text-ink/55">Loading schedule…</p>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="surface p-3">
      <p className="tlabel">{label}</p>
      <p
        className={`mt-0.5 text-lg font-semibold ${accent ? "text-forest" : "text-ink"}`}
      >
        {value}
      </p>
      {sub ? <p className="font-mono text-[11px] text-ink/50">{sub}</p> : null}
    </div>
  );
}

function Section({
  title,
  action,
  danger,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  danger?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <p className={`tlabel ${danger ? "!text-red-600" : ""}`}>{title}</p>
        {action}
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Bucket({
  title,
  danger,
  tasks,
  members,
  selectedId,
  busy,
  onSelect,
}: {
  title: string;
  danger?: boolean;
  tasks: Task[];
  members: Member[];
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <Section title={`${title} · ${tasks.length}`} danger={danger}>
      {tasks.map((t) => (
        <AgendaRow
          key={t.id}
          task={t}
          members={members}
          selected={t.id === selectedId}
          busy={busy}
          onSelect={() => onSelect(t.id)}
        />
      ))}
    </Section>
  );
}

function AgendaRow({
  task,
  members,
  selected,
  busy,
  onSelect,
  onApprove,
}: {
  task: Task;
  members: Member[];
  selected: boolean;
  busy: boolean;
  onSelect: () => void;
  onApprove?: () => void;
}) {
  const due = dueInfo(task.due_date);
  const clean = checkCount(task) === 0;
  return (
    <div
      className={`rounded-xl border bg-white p-3 transition ${
        selected ? "border-forest ring-2 ring-forest/15" : "border-ink/10"
      }`}
    >
      <button onClick={onSelect} className="block w-full text-left">
        <div className="flex items-center justify-between gap-2">
          <span className="tlabel">{KIND_LABEL[task.kind] ?? task.kind}</span>
          <StatusBadge status={task.status} />
        </div>
        <p className="mt-1 font-semibold text-ink">{task.title}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <AssigneeChip members={members} id={task.assignee_id} />
          {due && (
            <span
              className={`font-mono text-[11px] ${
                due.overdue ? "text-red-600" : "text-ink/50"
              }`}
            >
              {due.label}
            </span>
          )}
        </div>
      </button>
      {onApprove && (
        <div className="mt-2.5 flex gap-2">
          <button className="btn-green" disabled={busy} onClick={onApprove}>
            {clean ? "Approve" : "Approve anyway"}
          </button>
          <button className="btn-line" disabled={busy} onClick={onSelect}>
            Open
          </button>
        </div>
      )}
    </div>
  );
}
