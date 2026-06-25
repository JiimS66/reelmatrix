"use client";

import type { Task } from "@/lib/teamApi";

import { ScoreBadge } from "./primitives";

export function ContentPreview({ tasks }: { tasks: Task[] }) {
  const content = tasks.filter(
    (t) => (t.kind === "asset" || t.kind === "visual") && t.output,
  );
  if (content.length === 0) return null;
  return (
    <div className="surface p-4">
      <p className="tlabel">Content preview</p>
      <p className="mt-0.5 text-sm text-ink/60">
        Each channel&apos;s rendered post and visual, laid out as a feed.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {content.map((task) => (
          <PreviewCard key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}

function PreviewCard({ task }: { task: Task }) {
  const out = (task.output ?? {}) as Record<string, unknown>;
  const channel = String(out.channel ?? (task.params as { channel?: string })?.channel ?? "");

  if (task.kind === "visual") {
    const ref = String(out.image_ref ?? "");
    const isImageUrl = /^https?:\/\//.test(ref);
    return (
      <div className="overflow-hidden rounded-xl border border-ink/10 bg-white">
        {isImageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={ref} alt={String(out.alt_text ?? "")} className="aspect-square w-full object-cover" />
        ) : (
          <div className="flex aspect-square w-full flex-col items-center justify-center bg-canvas text-center">
            <div className="text-2xl">🖼</div>
            <p className="mt-1 px-3 font-mono text-[10px] text-ink/45">
              {String(out.aspect_ratio ?? "1:1")} · {ref || "generated"}
            </p>
          </div>
        )}
        <div className="p-2.5">
          <span className="chip border-forest/30 text-forest">{channel} · visual</span>
          {typeof out.concept === "string" && (
            <p className="mt-1.5 text-sm text-ink/80">{out.concept}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col rounded-xl border border-ink/10 bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="chip">{channel}</span>
        <ScoreBadge score={task.score} />
      </div>
      <p className="mt-1.5 font-semibold text-ink">{String(out.title ?? task.title)}</p>
      <p className="mt-1 line-clamp-5 whitespace-pre-line text-sm text-ink/70">
        {String(out.content ?? "")}
      </p>
      {typeof out.call_to_action === "string" && out.call_to_action && (
        <p className="mt-2 font-mono text-[11px] text-forest">→ {out.call_to_action}</p>
      )}
    </div>
  );
}
