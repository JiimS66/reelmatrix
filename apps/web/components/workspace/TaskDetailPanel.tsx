"use client";

import { useEffect, useState } from "react";

import {
  addAnnotation,
  addComment,
  assignTask,
  editTask,
  generateVideo,
  improvePost,
  lockTask,
  resolveAnnotation,
  reviewTask,
  submitTask,
  syncVisual,
  type ExecutionMode,
  type Member,
  type Task,
  type TaskDetail,
} from "@/lib/teamApi";

import { ClaimCheckView, type Claim } from "./ClaimCheckView";
import {
  AssigneeChip,
  CHECK_LABEL,
  KIND_LABEL,
  MODE_LABEL,
  ScoreBadge,
  StatusBadge,
  cap,
  checkCount,
  memberName,
  scoreBand,
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
  const isClaimCheck = task.kind === "claim_check";
  const output = (task.output ?? {}) as Record<string, unknown>;

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [cta, setCta] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [comment, setComment] = useState("");
  const [annotation, setAnnotation] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [mode, setMode] = useState<ExecutionMode | "">("");
  const [busy, setBusy] = useState(false);
  const [showDraft, setShowDraft] = useState(false);

  const visual = (output.visual ?? null) as Record<string, unknown> | null;

  useEffect(() => {
    setTitle(String(output.title ?? ""));
    setContent(String(output.content ?? ""));
    setCta(String(output.call_to_action ?? ""));
    setImageUrl(String(visual?.image_ref ?? ""));
    setVideoUrl(String(visual?.video_ref ?? ""));
    setJsonText(JSON.stringify(task.output ?? {}, null, 2));
    setComment("");
    setAnnotation("");
    setAssignTo("");
    setMode("");
    setShowDraft(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.id]);

  const can = (action: string) => detail.available_actions.includes(action);

  const claimChecks: Claim[] = (() => {
    try {
      const parsed = JSON.parse(jsonText);
      return Array.isArray(parsed?.claim_checks) ? parsed.claim_checks : [];
    } catch {
      return [];
    }
  })();
  function setClaims(next: Claim[]) {
    let base: Record<string, unknown> = {};
    try {
      base = JSON.parse(jsonText);
    } catch {
      /* keep {} */
    }
    setJsonText(JSON.stringify({ ...base, claim_checks: next }, null, 2));
  }
  const canEditClaims = can("edit") || can("submit");

  function buildOutput(): Record<string, unknown> | null {
    if (isAsset) {
      const nextVisual = {
        ...(visual ?? {}),
        ...(imageUrl ? { image_ref: imageUrl } : {}),
        ...(videoUrl ? { video_ref: videoUrl } : {}),
      };
      return {
        ...output,
        title,
        content,
        call_to_action: cta,
        ...(Object.keys(nextVisual).length > 0 ? { visual: nextVisual } : {}),
      };
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
  const onSyncVisual = () => run(() => syncVisual(currentMemberId, task.id));
  const onGenerateVideo = () => run(() => generateVideo(currentMemberId, task.id));
  const onImprove = () => run(() => improvePost(currentMemberId, task.id));
  const onLock = (locked: boolean) => run(() => lockTask(currentMemberId, task.id, locked));
  const onAddAnnotation = () => {
    if (annotation.trim())
      run(() => addAnnotation(currentMemberId, task.id, annotation.trim()));
  };
  const onResolve = (id: string, resolved: boolean) =>
    run(() => resolveAnnotation(currentMemberId, id, resolved));
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
            {task.locked && (
              <span className="chip border-amber-300 bg-amber-50 text-amber-700">🔒 Locked</span>
            )}
            <ScoreBadge score={task.score} />
            <StatusBadge status={task.status} />
          </div>
        </div>
        <h2 className="text-lg font-semibold text-ink">{task.title}</h2>
        <div className="flex flex-wrap items-center gap-2">
          <AssigneeChip members={members} id={task.assignee_id} />
          <span className="chip">{MODE_LABEL[task.execution_mode] ?? task.execution_mode}</span>
        </div>
        {(isAsset || isVisual) && <TargetingStrip task={task} />}
      </header>

      {/* Output editor */}
      <section className="space-y-2">
        <p className="tlabel">{isClaimCheck ? "Claim check — the truth rail" : "Output"}</p>
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

            {/* The post's visual — copy + image/video are one deliverable. */}
            <div className="rounded-xl border border-ink/10 bg-canvas/60 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="tlabel">Visual</p>
                {can("edit") && (
                  <div className="flex gap-1.5">
                    <button
                      className="btn-line px-2.5 py-1 text-xs"
                      disabled={busy}
                      onClick={onSyncVisual}
                    >
                      {busy ? "…" : "↻ Sync visual"}
                    </button>
                    <button
                      className="btn-line px-2.5 py-1 text-xs"
                      disabled={busy}
                      onClick={onGenerateVideo}
                    >
                      ▶ Generate video
                    </button>
                  </div>
                )}
              </div>
              {visual && <VisualPreview output={visual} />}
              {videoUrl.includes("mock-video") && (
                <p className="mt-1.5 font-mono text-[11px] text-forest">
                  🎬 reel rendered — scripted into scenes
                </p>
              )}
              <div className="mt-2 space-y-1.5">
                <input
                  className="field"
                  value={imageUrl}
                  placeholder="Image URL (or generated mock ref)"
                  onChange={(e) => setImageUrl(e.target.value)}
                />
                <input
                  className="field"
                  value={videoUrl}
                  placeholder="Video URL (human-attached)"
                  onChange={(e) => setVideoUrl(e.target.value)}
                />
              </div>
            </div>
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
        ) : isClaimCheck ? (
          <ClaimCheckView
            claims={claimChecks}
            onChange={setClaims}
            currentMemberId={currentMemberId}
            readOnly={!canEditClaims}
          />
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

      {task.predicted_performance && (
        <section className="space-y-1.5">
          <p className="tlabel">Predicted performance</p>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-sm font-semibold ${scoreBand(
                task.predicted_performance.overall,
              )}`}
            >
              {task.predicted_performance.overall}
            </span>
            {Object.entries(task.predicted_performance.factors).map(([k, v]) => (
              <span key={k} className="chip font-mono text-[10px]">
                {k} {v}
              </span>
            ))}
          </div>
          <p className="font-mono text-[10px] text-ink/45">
            {task.predicted_performance.note}
          </p>
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
        {isAsset && can("edit") && checkCount(task) > 0 && (
          <button className="btn-dark" disabled={busy} onClick={onImprove}>
            ✦ Apply AI improvement
          </button>
        )}
        {can("lock") && (
          <button className="btn-line" disabled={busy} onClick={() => onLock(true)}>
            🔒 Lock
          </button>
        )}
        {can("unlock") && (
          <button className="btn-line" disabled={busy} onClick={() => onLock(false)}>
            🔓 Unlock
          </button>
        )}
      </section>

      {/* Proofing: version stack + pinpoint annotations */}
      {(detail.versions.length > 0 || can("annotate")) && (
        <section className="space-y-2 border-t border-ink/10 pt-4">
          <p className="tlabel">Proofing</p>
          {detail.versions.length > 0 && (
            <p className="font-mono text-[11px] text-ink/55">
              {detail.versions.length} version{detail.versions.length === 1 ? "" : "s"}:{" "}
              {detail.versions.map((v) => `v${v.number} ${v.source}`).join(" · ")}
            </p>
          )}
          {detail.annotations.length > 0 && (
            <ul className="space-y-1.5">
              {detail.annotations.map((a) => (
                <li
                  key={a.id}
                  className={`flex items-start justify-between gap-2 rounded-lg border p-2 text-sm ${
                    a.resolved
                      ? "border-ink/10 bg-canvas text-ink/45 line-through"
                      : "border-amber-200 bg-amber-50/50 text-ink/80"
                  }`}
                >
                  <span>
                    {a.body}
                    {typeof a.anchor?.quote === "string" && (
                      <span className="ml-1 font-mono text-[10px] text-ink/40">
                        “{a.anchor.quote}”
                      </span>
                    )}
                  </span>
                  <button
                    className="shrink-0 font-mono text-[10px] text-forest hover:underline"
                    disabled={busy}
                    onClick={() => onResolve(a.id, !a.resolved)}
                  >
                    {a.resolved ? "reopen" : "resolve"}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {can("annotate") && (
            <div className="flex gap-2">
              <input
                className="field"
                value={annotation}
                placeholder="Pinpoint feedback…"
                onChange={(e) => setAnnotation(e.target.value)}
              />
              <button
                className="btn-line"
                disabled={busy || !annotation.trim()}
                onClick={onAddAnnotation}
              >
                Add note
              </button>
            </div>
          )}
        </section>
      )}

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

function TargetingStrip({ task }: { task: Task }) {
  const p = (task.params ?? {}) as Record<string, unknown>;
  const items = [
    p.segment && { label: "Segment", value: String(p.segment) },
    p.pain_point && { label: "Pain", value: String(p.pain_point) },
    p.angle && { label: "Hot topic", value: String(p.angle) },
    task.phase && { label: "Phase", value: cap(String(task.phase)) },
  ].filter(Boolean) as { label: string; value: string }[];
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 rounded-lg border border-ink/10 bg-canvas px-2.5 py-1.5">
      {items.map((it) => (
        <span key={it.label} className="font-mono text-[11px] text-ink/60">
          <span className="text-ink/40">{it.label}:</span> {it.value}
        </span>
      ))}
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
