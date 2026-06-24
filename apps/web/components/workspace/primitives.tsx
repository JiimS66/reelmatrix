import type { Member, Task, TaskStatus } from "@/lib/teamApi";

export const KIND_LABEL: Record<string, string> = {
  ideation: "Ideation",
  planning: "Planning",
  asset: "Asset",
  claim_check: "Claim check",
};

export const MODE_LABEL: Record<string, string> = {
  ai_auto: "AI auto",
  ai_draft_human_review: "AI draft → human review",
  human_only: "Human only",
};

export const ATOM_KIND_LABEL: Record<string, string> = {
  headline: "Headline",
  hook: "Hook",
  cta: "CTA",
  proof: "Proof",
  one_liner: "One-liner",
};

export const cap = (value: string): string =>
  value ? value.charAt(0).toUpperCase() + value.slice(1) : value;

export function dueInfo(
  due: string | null,
): { label: string; overdue: boolean } | null {
  if (!due) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${due}T00:00:00`);
  const days = Math.round((target.getTime() - today.getTime()) / 86_400_000);
  if (Number.isNaN(days)) return null;
  if (days < 0) return { label: `${-days}d overdue`, overdue: true };
  if (days === 0) return { label: "Due today", overdue: false };
  if (days === 1) return { label: "Due tomorrow", overdue: false };
  return { label: `Due in ${days}d`, overdue: false };
}

export function memberName(members: Member[], id: string | null): string {
  if (!id) return "Unassigned";
  return members.find((m) => m.id === id)?.display_name ?? "Unknown";
}

export function memberKind(
  members: Member[],
  id: string | null,
): "human" | "ai" | null {
  if (!id) return null;
  return members.find((m) => m.id === id)?.kind ?? null;
}

const STATUS_STYLE: Record<TaskStatus, string> = {
  todo: "bg-canvas text-ink/70 border-ink/10",
  in_progress: "bg-amber-50 text-amber-800 border-amber-200",
  needs_review: "bg-amber-100 text-amber-900 border-amber-300",
  done: "bg-emerald-50 text-emerald-800 border-emerald-200",
  blocked: "bg-red-50 text-red-700 border-red-200",
};

const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: "To do",
  in_progress: "In progress",
  needs_review: "Needs review",
  done: "Done",
  blocked: "Blocked",
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[11px] ${STATUS_STYLE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

// Colored left-border accent so done vs incomplete reads at a glance.
const STATUS_ACCENT: Record<TaskStatus, string> = {
  done: "border-l-emerald-400",
  needs_review: "border-l-amber-400",
  in_progress: "border-l-amber-300",
  blocked: "border-l-red-400",
  todo: "border-l-slate-300",
};

export function statusAccent(status: TaskStatus): string {
  return STATUS_ACCENT[status];
}

// Soft background tint to reinforce done (green) vs incomplete (amber/red).
const STATUS_TINT: Record<TaskStatus, string> = {
  done: "bg-emerald-50/50",
  needs_review: "bg-amber-50/60",
  in_progress: "bg-amber-50/40",
  blocked: "bg-red-50/50",
  todo: "bg-white",
};

export function statusTint(status: TaskStatus): string {
  return STATUS_TINT[status];
}

export function AssigneeChip({
  members,
  id,
}: {
  members: Member[];
  id: string | null;
}) {
  const kind = memberKind(members, id);
  const dot =
    kind === "ai" ? "bg-forest" : kind === "human" ? "bg-ink" : "bg-ink/30";
  const role = kind === "ai" ? "AI" : kind === "human" ? "Human" : "—";
  return (
    <span className="chip">
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {role} · {memberName(members, id)}
    </span>
  );
}

export function checkCount(task: Task): number {
  return Object.values(task.checks || {}).reduce(
    (n, arr) => n + (arr?.length ?? 0),
    0,
  );
}

export function CheckBadges({ task }: { task: Task }) {
  const groups = Object.entries(task.checks || {});
  if (groups.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {groups.map(([name, issues]) => {
        const n = issues?.length ?? 0;
        const ok = n === 0;
        return (
          <span
            key={name}
            className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-[10px] ${
              ok
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-amber-300 bg-amber-50 text-amber-800"
            }`}
          >
            {ok ? "✓" : n} {cap(name)}
          </span>
        );
      })}
    </div>
  );
}
