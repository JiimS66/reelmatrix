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
