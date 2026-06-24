"use client";

import { useState } from "react";

import type { PerformanceData } from "@/lib/teamApi";

function pct(n: number, d: number): string {
  return d > 0 ? `${((n / d) * 100).toFixed(1)}%` : "—";
}

export function PerformanceView({
  data,
  canSync = false,
  onSync,
  onPublish,
}: {
  data: PerformanceData;
  canSync?: boolean;
  onSync?: () => Promise<void> | void;
  onPublish?: () => Promise<void> | void;
}) {
  const totals = data.totals;
  const impressions = totals.impressions ?? 0;
  const clicks = totals.clicks ?? 0;
  const signups = totals.signups ?? 0;
  const [busy, setBusy] = useState<"sync" | "publish" | null>(null);

  async function run(kind: "sync" | "publish", fn?: () => Promise<void> | void) {
    if (!fn) return;
    setBusy(kind);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
        <span>{data.note}</span>
        {canSync && (
          <div className="flex gap-2">
            {onPublish && (
              <button
                className="btn-line px-2.5 py-1 text-xs"
                disabled={busy !== null}
                onClick={() => run("publish", onPublish)}
              >
                {busy === "publish" ? "Publishing…" : "Publish all ↑"}
              </button>
            )}
            {onSync && (
              <button
                className="btn-line px-2.5 py-1 text-xs"
                disabled={busy !== null}
                onClick={() => run("sync", onSync)}
              >
                {busy === "sync" ? "Syncing…" : "Sync GA4 ↻"}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="Impressions" value={impressions.toLocaleString()} />
        <Tile
          label="Clicks"
          value={clicks.toLocaleString()}
          sub={`CTR ${pct(clicks, impressions)}`}
        />
        <Tile
          label="Signups"
          value={signups.toLocaleString()}
          sub={`Conv ${pct(signups, clicks)}`}
          accent
        />
        <Tile label="Platforms" value={String(data.platforms.length)} />
      </div>

      {data.platforms.length === 0 ? (
        <p className="surface p-6 text-sm text-ink/60">
          No published posts yet. Approve an asset to publish it — its post and
          metrics land here, grouped by platform.
        </p>
      ) : (
        data.platforms.map((platform) => (
          <div key={platform.platform} className="surface overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink/10 px-4 py-2.5">
              <p className="font-semibold text-ink">{platform.platform}</p>
              <p className="font-mono text-[11px] text-ink/55">
                {platform.impressions.toLocaleString()} impr ·{" "}
                {platform.clicks.toLocaleString()} clicks ·{" "}
                <span className="text-forest">
                  {platform.signups.toLocaleString()} signups
                </span>
              </p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink/5 text-left font-mono text-[11px] text-ink/45">
                  <th className="px-4 py-1.5 font-normal">Post</th>
                  <th className="px-3 py-1.5 text-right font-normal">Impr.</th>
                  <th className="px-3 py-1.5 text-right font-normal">Clicks</th>
                  <th className="px-3 py-1.5 text-right font-normal">Signups</th>
                  <th className="px-4 py-1.5 font-normal">Link</th>
                </tr>
              </thead>
              <tbody>
                {platform.posts.map((post) => (
                  <tr key={post.post_id} className="border-b border-ink/5 last:border-0">
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-ink">{post.title}</p>
                        <PublishPill status={post.publish_status} permalink={post.permalink} />
                      </div>
                      <p className="font-mono text-[11px] text-ink/45">
                        {post.published_at} · {post.source}
                      </p>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-[12px]">
                      {post.impressions.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-[12px]">
                      {post.clicks.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-[12px] font-semibold text-forest">
                      {post.signups.toLocaleString()}
                    </td>
                    <td className="max-w-xs px-4 py-2">
                      <a
                        href={post.url}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate font-mono text-[11px] text-ink/50 hover:text-ink hover:underline"
                        title={post.url}
                      >
                        {post.url}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}

function PublishPill({
  status,
  permalink,
}: {
  status: string;
  permalink: string | null;
}) {
  const label =
    status === "published"
      ? "Published"
      : status === "scheduled"
        ? "Scheduled"
        : status === "failed"
          ? "Failed"
          : "Draft";
  const cls =
    status === "published"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : status === "failed"
        ? "border-red-200 bg-red-50 text-red-700"
        : "border-ink/10 bg-canvas text-ink/50";
  return (
    <span
      title={permalink ?? undefined}
      className={`inline-flex items-center rounded-full border px-1.5 py-0.5 font-mono text-[10px] ${cls}`}
    >
      {label}
    </span>
  );
}

function Tile({
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
