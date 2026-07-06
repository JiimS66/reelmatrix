"use client";

import { useEffect, useState } from "react";

import {
  acceptAction,
  getActions,
  ignoreAction,
  planActions,
  type PlannedAction,
} from "@/lib/teamApi";

/** Phase 14 — the front-end face of the marketing brain: the orchestrator reads every
 * signal (flywheel / funnel / segments / market / reliability) and ranks the next moves;
 * the human Accepts or Ignores. Density rule: the title decides; the why is one tap away. */
export function AgentInbox({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [actions, setActions] = useState<PlannedAction[]>([]);
  const [busy, setBusy] = useState(false);
  const [openWhy, setOpenWhy] = useState<string | null>(null);

  useEffect(() => {
    getActions(memberId)
      .then(setActions)
      .catch(() => {});
  }, [memberId]);

  if (!canManage) return null;

  async function run(fn: () => Promise<PlannedAction[]>) {
    setBusy(true);
    try {
      setActions(await fn());
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="tlabel">Agent Inbox — proposed next moves</p>
        <button
          className="btn-line shrink-0 px-2.5 py-1 text-xs"
          disabled={busy}
          onClick={() => run(() => planActions(memberId))}
        >
          {busy ? "Thinking…" : "Plan next moves ↻"}
        </button>
      </div>
      {actions.length === 0 ? (
        <p className="mt-3 text-sm text-ink/50">
          No proposals yet — click &ldquo;Plan next moves&rdquo;.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {actions.map((a) => (
            <li key={a.id} className="rounded-lg border border-ink/10 bg-canvas p-3">
              <div className="flex items-start justify-between gap-3">
                <button
                  className="min-w-0 text-left"
                  onClick={() => setOpenWhy((prev) => (prev === a.id ? null : a.id))}
                  title="Show why the orchestrator proposes this"
                >
                  <p className="text-sm font-medium text-ink">
                    {a.title}
                    <span className="ml-1.5 font-mono text-[11px] text-ink/35">
                      {openWhy === a.id ? "▴" : "why ▾"}
                    </span>
                  </p>
                </button>
                <PriorityMeter priority={a.priority} />
              </div>
              {openWhy === a.id && (
                <p className="mt-1.5 rounded-md bg-white px-2.5 py-1.5 text-[12px] leading-5 text-ink/60">
                  {a.rationale}
                </p>
              )}
              <div className="mt-2 flex items-center gap-2">
                <button
                  className="btn-green px-2.5 py-0.5 text-[11px]"
                  disabled={busy}
                  onClick={() => run(() => acceptAction(memberId, a.id))}
                >
                  Accept
                </button>
                <button
                  className="btn-line px-2.5 py-0.5 text-[11px]"
                  disabled={busy}
                  onClick={() => run(() => ignoreAction(memberId, a.id))}
                >
                  Ignore
                </button>
                <span className="ml-auto font-mono text-[11px] text-ink/40">
                  {a.type.replaceAll("_", " ")}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Priority as a shape, not a number: 5 ticks, filled from the left. */
function PriorityMeter({ priority }: { priority: number }) {
  const filled = Math.max(1, Math.min(5, Math.round(priority / 20)));
  return (
    <div
      className="flex shrink-0 items-center gap-0.5 pt-1"
      title={`Priority ${priority}/100`}
    >
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={`h-2.5 w-1 rounded-sm ${i <= filled ? "bg-forest" : "bg-ink/10"}`}
        />
      ))}
    </div>
  );
}
