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
 * the human Accepts or Ignores. Inverts the "panel swamp" into one decision queue. */
export function AgentInbox({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [actions, setActions] = useState<PlannedAction[]>([]);
  const [busy, setBusy] = useState(false);

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
        <div>
          <p className="tlabel">Agent Inbox — what the brain proposes next</p>
          <p className="mt-0.5 text-sm text-ink/55">
            The orchestrator reads every signal and ranks the next moves; you decide.
          </p>
        </div>
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
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink">{a.title}</p>
                  <p className="mt-0.5 text-[12px] text-ink/55">{a.rationale}</p>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-forest">
                  P{a.priority}
                </span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  className="btn-line px-2.5 py-0.5 text-[11px]"
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
                <span className="ml-auto font-mono text-[10px] text-ink/40">{a.type}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
