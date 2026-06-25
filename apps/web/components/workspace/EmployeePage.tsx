"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getMemberMessages,
  getMemberProfile,
  sendMemberMessage,
  type DirectMessage,
  type MemberProfile,
} from "@/lib/teamApi";

import { KIND_LABEL, ScoreBadge, StatusBadge, scoreBand } from "./primitives";

export function EmployeePage({
  memberId,
  currentMemberId,
  isLead,
  onBack,
  onOpenTask,
  onError,
}: {
  memberId: string;
  currentMemberId: string;
  isLead: boolean;
  onBack: () => void;
  onOpenTask: (taskId: string) => void;
  onError: (message: string) => void;
}) {
  const [profile, setProfile] = useState<MemberProfile | null>(null);
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"message" | "directive">("message");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setProfile(await getMemberProfile(currentMemberId, memberId));
      setMessages(await getMemberMessages(currentMemberId, memberId));
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not load the employee.");
    }
  }, [memberId, currentMemberId, onError]);

  useEffect(() => {
    load();
  }, [load]);

  async function send() {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const thread = await sendMemberMessage(currentMemberId, memberId, {
        body: text.trim(),
        kind: mode,
        title: mode === "directive" ? title.trim() || null : null,
      });
      setMessages(thread);
      setText("");
      setTitle("");
      setProfile(await getMemberProfile(currentMemberId, memberId));
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not send the message.");
    } finally {
      setBusy(false);
    }
  }

  if (!profile) return <p className="surface p-6 text-sm text-ink/60">Loading…</p>;
  const m = profile.member;
  const isAI = m.kind === "ai";
  const stat = profile.fleet;

  return (
    <div className="space-y-5">
      <button onClick={onBack} className="tlabel hover:underline">
        ← Back to team
      </button>

      <div className="surface p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold text-ink">{m.display_name}</h2>
          <span className="chip">
            <span
              className={`h-1.5 w-1.5 rounded-full ${isAI ? "bg-forest" : "bg-ink"}`}
            />
            {isAI ? "AI" : "Human"}
          </span>
          {isAI && m.provider && (
            <span className="chip border-forest/30 text-forest">
              {m.provider}
              {m.model ? ` · ${m.model}` : ""}
            </span>
          )}
        </div>
        {m.job_description && (
          <p className="mt-2 max-w-2xl text-sm text-ink/70">{m.job_description}</p>
        )}
        {m.handles_kinds.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {m.handles_kinds.map((k) => (
              <span key={k} className="chip">
                {KIND_LABEL[k] ?? k}
              </span>
            ))}
          </div>
        )}
        {isAI && stat && (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="LLM calls" value={stat.runs} />
            <Stat label="Tasks owned" value={stat.tasks_owned} />
            <Stat
              label="Avg score"
              value={stat.avg_score ?? "—"}
              band={stat.avg_score ?? undefined}
            />
            <Stat label="Self-corrections" value={stat.self_corrections} />
          </div>
        )}
      </div>

      {profile.tasks.length > 0 && (
        <div className="surface p-4">
          <p className="tlabel">Their work</p>
          <ul className="mt-2 space-y-1.5">
            {profile.tasks.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => onOpenTask(t.id)}
                  className="flex w-full items-center justify-between gap-2 rounded-lg border border-ink/10 bg-canvas px-3 py-2 text-left text-sm hover:border-ink/25"
                >
                  <span className="truncate">
                    <span className="tlabel mr-2">{KIND_LABEL[t.kind] ?? t.kind}</span>
                    {t.title}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <ScoreBadge score={t.score} />
                    <StatusBadge status={t.status} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="surface p-4">
        <p className="tlabel">Direct line</p>
        <p className="mt-0.5 text-sm text-ink/60">
          {isAI
            ? "Message your AI employee or hand off a task — they reply in role."
            : "Leave a message or assign a task."}
        </p>

        <div className="mt-3 space-y-2">
          {messages.length === 0 ? (
            <p className="text-sm text-ink/45">No messages yet.</p>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                  msg.sender === "lead"
                    ? "ml-auto bg-forest text-white"
                    : "bg-canvas text-ink"
                }`}
              >
                {msg.kind === "directive" && (
                  <p
                    className={`mb-0.5 font-mono text-[10px] ${
                      msg.sender === "lead" ? "text-white/70" : "text-forest"
                    }`}
                  >
                    📋 Task{msg.title ? `: ${msg.title}` : ""}
                    {msg.task_id ? " · tracked ✓" : ""}
                  </p>
                )}
                {msg.body}
              </div>
            ))
          )}
        </div>

        {isLead && (
          <div className="mt-3 space-y-2 border-t border-ink/10 pt-3">
            <div className="flex gap-1.5">
              {(["message", "directive"] as const).map((mo) => (
                <button
                  key={mo}
                  onClick={() => setMode(mo)}
                  className={`rounded-full px-3 py-1 font-mono text-[11px] transition ${
                    mode === mo
                      ? "bg-ink text-white"
                      : "border border-ink/15 bg-white text-ink/70 hover:text-ink"
                  }`}
                >
                  {mo === "message" ? "Message" : "Assign task"}
                </button>
              ))}
            </div>
            {mode === "directive" && (
              <input
                className="field"
                value={title}
                placeholder="Task title"
                onChange={(e) => setTitle(e.target.value)}
              />
            )}
            <div className="flex gap-2">
              <input
                className="field"
                value={text}
                placeholder={mode === "directive" ? "What should they do?" : "Message…"}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
              />
              <button className="btn-dark" disabled={busy || !text.trim()} onClick={send}>
                {busy ? "…" : "Send"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  band,
}: {
  label: string;
  value: string | number;
  band?: number;
}) {
  return (
    <div className="rounded-lg border border-ink/10 bg-canvas p-2.5">
      <p className="tlabel">{label}</p>
      {typeof band === "number" ? (
        <span
          className={`mt-0.5 inline-flex items-center rounded-md border px-1.5 py-0.5 font-mono text-sm font-semibold ${scoreBand(
            band,
          )}`}
        >
          {value}
        </span>
      ) : (
        <p className="mt-0.5 font-mono text-lg font-semibold text-ink">{value}</p>
      )}
    </div>
  );
}
