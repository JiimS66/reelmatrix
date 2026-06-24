"use client";

import type { Board, Member, Task } from "@/lib/teamApi";

import {
  AssigneeChip,
  CheckBadges,
  KIND_LABEL,
  StatusBadge,
  checkCount,
  dueInfo,
  memberKind,
} from "./primitives";

interface HomeViewProps {
  role: "lead" | "member";
  board: Board | null;
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
  if (role === "member") {
    return (
      <MemberHome
        inbox={inbox}
        members={members}
        selectedId={selectedId}
        busy={busy}
        onSelect={onSelect}
      />
    );
  }

  if (!board) {
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
  const reviews = tasks.filter((t) => t.status === "needs_review");
  const cleanReviews = reviews.filter((t) => checkCount(t) === 0);
  const mine = tasks.filter(
    (t) =>
      t.assignee_id === currentMemberId &&
      (t.status === "todo" || t.status === "in_progress"),
  );
  const spotCheck = tasks.filter(
    (t) =>
      t.status === "done" &&
      t.kind === "asset" &&
      memberKind(members, t.assignee_id) === "ai",
  );
  const flagged = tasks.filter(
    (t) => t.status === "blocked" || (t.status !== "done" && checkCount(t) > 0),
  );

  const empty =
    reviews.length === 0 &&
    mine.length === 0 &&
    spotCheck.length === 0 &&
    flagged.length === 0;

  return (
    <div className="space-y-6">
      {reviews.length > 0 && (
        <Section
          title={`Reviews waiting · ${reviews.length}`}
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
          {reviews.map((task) => (
            <QueueRow
              key={task.id}
              task={task}
              members={members}
              selected={task.id === selectedId}
              busy={busy}
              onSelect={() => onSelect(task.id)}
              onApprove={() => onApprove(task.id)}
            />
          ))}
        </Section>
      )}

      {mine.length > 0 && (
        <Section title={`Your tasks · ${mine.length}`}>
          {mine.map((task) => (
            <QueueRow
              key={task.id}
              task={task}
              members={members}
              selected={task.id === selectedId}
              busy={busy}
              onSelect={() => onSelect(task.id)}
            />
          ))}
        </Section>
      )}

      {spotCheck.length > 0 && (
        <Section title={`AI drafted — give it a look · ${spotCheck.length}`}>
          {spotCheck.map((task) => (
            <QueueRow
              key={task.id}
              task={task}
              members={members}
              selected={task.id === selectedId}
              busy={busy}
              onSelect={() => onSelect(task.id)}
            />
          ))}
        </Section>
      )}

      {flagged.length > 0 && (
        <Section title={`Needs attention · ${flagged.length}`}>
          {flagged.map((task) => (
            <QueueRow
              key={task.id}
              task={task}
              members={members}
              selected={task.id === selectedId}
              busy={busy}
              onSelect={() => onSelect(task.id)}
            />
          ))}
        </Section>
      )}

      {empty && (
        <div className="surface p-6">
          <p className="tlabel">All clear</p>
          <p className="mt-1 text-sm text-ink/60">
            Nothing is waiting on you. Open the Board to spot-check the AI&apos;s
            work, or the Calendar to see what&apos;s coming up.
          </p>
        </div>
      )}
    </div>
  );
}

function MemberHome({
  inbox,
  members,
  selectedId,
  busy,
  onSelect,
}: {
  inbox: Task[];
  members: Member[];
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
}) {
  const sorted = [...inbox].sort((a, b) =>
    (a.due_date ?? "9999").localeCompare(b.due_date ?? "9999"),
  );
  if (sorted.length === 0) {
    return (
      <p className="surface p-6 text-sm text-ink/60">
        Nothing assigned to you right now. When the lead assigns you a task it
        lands here.
      </p>
    );
  }
  return (
    <Section title={`My tasks · ${sorted.length}`}>
      {sorted.map((task) => (
        <QueueRow
          key={task.id}
          task={task}
          members={members}
          selected={task.id === selectedId}
          busy={busy}
          onSelect={() => onSelect(task.id)}
        />
      ))}
    </Section>
  );
}

function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="tlabel">{title}</p>
        {action}
      </div>
      <div className="space-y-2.5">{children}</div>
    </section>
  );
}

function QueueRow({
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
  const clean = checkCount(task) === 0;
  const due = dueInfo(task.due_date);
  return (
    <div
      className={`rounded-2xl border bg-white p-4 transition ${
        selected ? "border-forest ring-2 ring-forest/15" : "border-ink/10"
      }`}
    >
      <button onClick={onSelect} className="block w-full text-left">
        <div className="flex items-center justify-between gap-3">
          <span className="tlabel">{KIND_LABEL[task.kind] ?? task.kind}</span>
          <StatusBadge status={task.status} />
        </div>
        <p className="mt-1.5 font-semibold text-ink">{task.title}</p>
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
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
        <div className="mt-2">
          <CheckBadges task={task} />
        </div>
      </button>
      {onApprove && (
        <div className="mt-3 flex gap-2">
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
