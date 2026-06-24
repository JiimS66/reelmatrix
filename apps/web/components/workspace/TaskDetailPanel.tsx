"use client";

import { useEffect, useState } from "react";

import {
  addComment,
  assignTask,
  editTask,
  reviewTask,
  submitTask,
  type ExecutionMode,
  type Member,
  type TaskDetail,
} from "@/lib/teamApi";

import {
  AssigneeChip,
  CHECK_LABEL,
  KIND_LABEL,
  MODE_LABEL,
  ScoreBadge,
  StatusBadge,
  cap,
  memberName,
} from "./primitives";

interface Props {
  detail: TaskDetail;
  members: Member[];
  currentMemberId: string;
  onChanged: () => void;
  onError: (message: string) => void;
}

const MODES: ExecutionMode[] = ["ai_auto", "ai_draft_human_review", "human_only"];

export function TaskDetailPanel({
  detail,
  members,
  currentMemberId,
  onChanged,
  onError,
}: Props) {
  const task = detail.task;
  const isAsset = task.kind === "asset";
  const isVisual = task.kind === "visual";
  const output = (task.output ?? {}) as Record<string, unknown>;

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [cta, setCta] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [comment, setComment] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [mode, setMode] = useState<ExecutionMode | "">("");
  const [busy, setBusy] = useState(false);
  const [showDraft, setShowDraft] = useState(false);

  useEffect(() => {
    setTitle(String(output.title ?? ""));
    setContent(String(output.content ?? ""));
    setCta(String(output.call_to_action ?? ""));
    setJsonText(JSON.stringify(task.output ?? {}, null, 2));
    setComment("");
    setAssignTo("");
    setMode("");
    setShowDraft(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.id]);

  const can = (action: string) => detail.available_actions.includes(action);

  function buildOutput(): Record<string, unknown> | null {
    if (isAsset) {
      return { ...output, title, content, call_to_action: cta };
    }
    try {
      const parsed: unknown = JSON.parse(jsonText);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        onError("Output must be a JSON object — fix it before saving.");
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch {
      onError("Output is not valid JSON — fix it before saving.");
      return null;
    }
  }

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      await fn();
      onChanged();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  const onSave = () => {
    const out = buildOutput();
    if (out) run(() => editTask(currentMemberId, task.id, out));
  };
  const onApprove = () => {
    const out = buildOutput();
    if (out) run(() => reviewTask(currentMemberId, task.id, { action: "approve", output: out }));
  };
  const onRequestChanges = () =>
    run(() => reviewTask(currentMemberId, task.id, { action: "request_changes" }));
  const onSubmit = () => {
    const out = buildOutput();
    if (out) run(() => submitTask(currentMemberId, task.id, out));
  };
  const onComment = () => {
    if (comment.trim()) run(() => addComment(currentMemberId, task.id, comment.trim()));
  };
  const onAssign = () =>
    run(() =>
      assignTask(currentMemberId, task.id, {
        member_id: assignTo || undefined,
        execution_mode: (mode || undefined) as ExecutionMode | undefined,
      }),
    );

  return (
    <div className="space-y-5">
      <header className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <span className="tlabel">{KIND_LABEL[task.kind] ?? task.kind}</span>
          <div className="flex items-center gap-2">
            <ScoreBadge score={task.score} />
            <StatusBadge status={task.status} />
          </div>
        </div>
        <h2 className="text-lg font-semibold text-ink">{task.title}</h2>
        <div className="flex flex-wrap items-center gap-2">
          <AssigneeChip members={members} id={task.assignee_id} />
          <span className="chip">{MODE_LABEL[task.execution_mode] ?? task.execution_mode}</span>
        </div>
      </header>

      {/* Output editor */}
      <section className="space-y-2">
        <p className="tlabel">Output</p>
        {isAsset ? (
          <div className="space-y-2">
            <input
              className="field font-semibold"
              value={title}
              placeholder="Title"
              onChange={(e) => setTitle(e.target.value)}
            />
            <textarea
              className="field min-h-40 resize-y font-mono text-[13px] leading-6"
              value={content}
              placeholder="Body copy"
              onChange={(e) => setContent(e.target.value)}
            />
            <input
              className="field"
              value={cta}
              placeholder="Call to action"
              onChange={(e) => setCta(e.target.value)}
            />
          </div>
        ) : isVisual ? (
          <div className="space-y-2">
            <VisualPreview output={output} />
            <textarea
              className="field min-h-32 resize-y font-mono text-[12px] leading-5"
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
            />
          </div>
        ) : (
          <textarea
            className="field min-h-56 resize-y font-mono text-[12px] leading-5"
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
          />
        )}
      </section>

      {/* Checks */}
      {Object.keys(task.checks || {}).length > 0 && (
        <section className="space-y-2">
          <p className="tlabel">Checks</p>
          <div className="space-y-1.5">
            {Object.entries(task.checks).map(([name, issues]) => (
              <div key={name} className="text-sm">
                <span className="font-mono text-[12px] text-ink/60">
                  {CHECK_LABEL[name] ?? cap(name)}:{" "}
                </span>
                {issues.length === 0 ? (
                  <span className="text-emerald-700">clean</span>
                ) : (
                  <ul className="mt-1 space-y-1">
                    {issues.map((issue, i) => (
                      <li key={i} className="text-amber-800">
                        — {issue.detail}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* AI original draft */}
      {detail.ai_draft && (
        <section>
          <button
            type="button"
            className="tlabel underline-offset-2 hover:underline"
            onClick={() => setShowDraft((v) => !v)}
          >
            {showDraft ? "Hide" : "Show"} AI original draft
          </button>
          {showDraft && (
            <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-ink/10 bg-canvas p-3 font-mono text-[11px] leading-5 text-ink/80">
              {JSON.stringify(detail.ai_draft, null, 2)}
            </pre>
          )}
        </section>
      )}

      {/* Actions */}
      <section className="flex flex-wrap gap-2 border-t border-ink/10 pt-4">
        {can("review") && (
          <>
            <button className="btn-green" disabled={busy} onClick={onApprove}>
              Approve
            </button>
            <button className="btn-line" disabled={busy} onClick={onRequestChanges}>
              Request changes
            </button>
          </>
        )}
        {can("edit") && (
          <button className="btn-dark" disabled={busy} onClick={onSave}>
            Save edit
          </button>
        )}
        {can("submit") && (
          <button className="btn-green" disabled={busy} onClick={onSubmit}>
            Submit
          </button>
        )}
      </section>

      {/* Assign / take over */}
      {can("assign") && (
        <section className="space-y-2 rounded-lg border border-ink/10 bg-canvas/60 p-3">
          <p className="tlabel">Reassign / change mode</p>
          <div className="flex flex-wrap gap-2">
            <select
              className="field max-w-48"
              value={assignTo}
              onChange={(e) => setAssignTo(e.target.value)}
            >
              <option value="">Keep assignee</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.display_name} ({m.kind})
                </option>
              ))}
            </select>
            <select
              className="field max-w-56"
              value={mode}
              onChange={(e) => setMode(e.target.value as ExecutionMode | "")}
            >
              <option value="">Keep mode</option>
              {MODES.map((mo) => (
                <option key={mo} value={mo}>
                  {MODE_LABEL[mo] ?? mo}
                </option>
              ))}
            </select>
            <button
              className="btn-line"
              disabled={busy || (!assignTo && !mode)}
              onClick={onAssign}
            >
              Apply
            </button>
          </div>
        </section>
      )}

      {/* Comments */}
      <section className="space-y-2">
        <p className="tlabel">Discussion</p>
        {detail.comments.length > 0 && (
          <ul className="space-y-2">
            {detail.comments.map((c) => (
              <li key={c.id} className="rounded-lg border border-ink/10 bg-white p-2.5 text-sm">
                <span className="font-mono text-[11px] text-ink/50">
                  {memberName(members, c.author_id)}
                </span>
                <p className="mt-0.5 text-ink">{c.body}</p>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <input
            className="field"
            placeholder="Add a comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button className="btn-line" disabled={busy || !comment.trim()} onClick={onComment}>
            Post
          </button>
        </div>
      </section>

      {/* Activity */}
      {detail.events.length > 0 && (
        <section className="space-y-1.5">
          <p className="tlabel">Activity</p>
          <ul className="space-y-1 font-mono text-[11px] text-ink/55">
            {detail.events.slice(-8).map((e) => (
              <li key={e.id}>
                {e.type}
                {e.actor_id ? ` · ${memberName(members, e.actor_id)}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function VisualPreview({ output }: { output: Record<string, unknown> }) {
  const ref = String(output.image_ref ?? "");
  const alt = String(output.alt_text ?? "");
  const isImageUrl = /^https?:\/\//.test(ref);
  return (
    <div className="space-y-2">
      {isImageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={ref}
          alt={alt}
          className="w-full rounded-lg border border-ink/10"
        />
      ) : (
        <div className="flex aspect-square w-full max-w-[16rem] flex-col items-center justify-center rounded-lg border border-dashed border-ink/25 bg-canvas text-center">
          <div className="text-2xl">🖼</div>
          <p className="mt-1 px-3 font-mono text-[11px] text-ink/55">
            {ref || "no image"}
          </p>
          <p className="font-mono text-[10px] text-ink/40">
            {String(output.aspect_ratio ?? "1:1")} · generated
          </p>
        </div>
      )}
      {typeof output.concept === "string" && (
        <p className="text-sm text-ink">
          <span className="tlabel">Concept</span> {output.concept}
        </p>
      )}
      {typeof output.prompt === "string" && (
        <div>
          <p className="tlabel">Prompt</p>
          <p className="mt-0.5 rounded-lg border border-ink/10 bg-canvas p-2 font-mono text-[12px] leading-5 text-ink/80">
            {output.prompt}
          </p>
        </div>
      )}
      {alt && <p className="text-xs text-ink/55">Alt: {alt}</p>}
    </div>
  );
}
