"use client";

import { useMemo, useState } from "react";

import {
  dispatchIntegration,
  type IntegrationDispatchResult,
  type PerformanceData,
} from "@/lib/teamApi";
import {
  ConversionBars,
  MomentumArea,
  RankedBarChart,
  ShareDonut,
} from "./charts";

function pct(n: number, d: number): string {
  return d > 0 ? `${((n / d) * 100).toFixed(1)}%` : "—";
}

function rate(n: number, d: number): number {
  return d > 0 ? Number(((n / d) * 100).toFixed(1)) : 0;
}

function money(n: number): string {
  return `$${Math.round(n).toLocaleString()}`;
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
  const [valuePerSignup, setValuePerSignup] = useState(120);
  const [showDetail, setShowDetail] = useState(false);

  const rows = useMemo(
    () =>
      [...data.platforms]
        .map((p) => ({
          platform: p.platform,
          impressions: p.impressions,
          clicks: p.clicks,
          signups: p.signups,
          ctr: rate(p.clicks, p.impressions),
          conv: rate(p.signups, p.clicks),
        }))
        .sort((a, b) => b.signups - a.signups),
    [data.platforms],
  );

  const momentum = useMemo(() => {
    const posts = data.platforms
      .flatMap((p) => p.posts)
      .filter((post) => post.published_at)
      .sort((a, b) => a.published_at.localeCompare(b.published_at));
    let running = 0;
    return posts.map((post) => {
      running += post.signups;
      return { date: post.published_at.slice(5, 10), cumulative: running };
    });
  }, [data.platforms]);

  const best = rows[0];
  const bestShare = signups > 0 && best ? Math.round((best.signups / signups) * 100) : 0;
  const totalPipeline = signups * valuePerSignup;

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
        <Tile
          label="Modeled pipeline"
          value={money(totalPipeline)}
          sub={`at $${valuePerSignup}/signup`}
          accent
        />
      </div>

      {rows.length === 0 ? (
        <p className="surface p-6 text-sm text-ink/60">
          No published posts yet. Approve an asset to publish it — its post and
          metrics land here, grouped by platform.
        </p>
      ) : (
        <>
          <section className="surface p-4 sm:p-5">
            <p className="eyebrow">Where signups come from</p>
            <div className="mt-3 grid items-center gap-4 md:grid-cols-[220px,1fr]">
              <ShareDonut
                data={rows.map((r) => ({ name: r.platform, value: r.signups }))}
                totalLabel="signups"
              />
              <div>
                <RankedBarChart
                  data={rows}
                  labelKey="platform"
                  valueKey="signups"
                  height={Math.max(110, rows.length * 40)}
                />
                {best && (
                  <p className="mt-1 px-1 text-sm text-ink/70">
                    <span className="font-semibold text-forest">{best.platform}</span>{" "}
                    brings in {bestShare}% of signups — your strongest channel right
                    now.
                  </p>
                )}
              </div>
            </div>
          </section>

          <div className="grid gap-5 lg:grid-cols-2">
            <section className="surface p-4 sm:p-5">
              <p className="eyebrow">Which platform converts best</p>
              <div className="mt-3">
                <ConversionBars data={rows} />
              </div>
            </section>

            <section className="surface p-4 sm:p-5">
              <p className="eyebrow">Momentum</p>
              {momentum.length >= 2 ? (
                <div className="mt-3">
                  <MomentumArea data={momentum} />
                  <p className="mt-1 px-1 font-mono text-[11px] text-ink/50">
                    Signups accumulating as posts ship.
                  </p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-ink/60">
                  Ship a second post and the momentum curve appears here.
                </p>
              )}
            </section>
          </div>

          <section className="surface p-4 sm:p-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <p className="eyebrow">Modeled revenue by platform</p>
              <label className="flex items-center gap-2 text-sm text-ink/70">
                Value per signup
                <input
                  type="range"
                  min={20}
                  max={500}
                  step={10}
                  value={valuePerSignup}
                  onChange={(e) => setValuePerSignup(Number(e.target.value))}
                  className="w-36 accent-forest"
                />
                <span className="w-12 font-mono text-[12px] font-semibold text-forest">
                  ${valuePerSignup}
                </span>
              </label>
            </div>
            <div className="mt-3">
              <RankedBarChart
                data={rows.map((r) => ({
                  platform: r.platform,
                  revenue: r.signups * valuePerSignup,
                }))}
                labelKey="platform"
                valueKey="revenue"
                unit=" USD"
                height={Math.max(110, rows.length * 40)}
                color="#1f6f52"
              />
            </div>
            <p className="mt-1 px-1 font-mono text-[11px] text-ink/50">
              Modeled: live signup counts × your value per signup. Connect your CRM
              for actuals.
            </p>
          </section>

          <IntegrationsCard
            campaignId={data.campaign_id}
            defaultTitle={
              best
                ? `[ReelMatrix] ${best.platform} recap — ${best.signups} signups`
                : "[ReelMatrix] Campaign results recap"
            }
            defaultBody={rows
              .map(
                (r) =>
                  `${r.platform}: ${r.impressions.toLocaleString()} impressions · ${r.clicks.toLocaleString()} clicks · ${r.signups} signups (${money(r.signups * valuePerSignup)} modeled)`,
              )
              .join("\n")}
          />

          <section className="surface overflow-hidden">
            <button
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-ink hover:bg-canvas"
              onClick={() => setShowDetail((v) => !v)}
            >
              Post-level detail
              <span className="font-mono text-[11px] text-ink/50">
                {showDetail ? "Hide ▴" : `${rows.length} platforms ▾`}
              </span>
            </button>
            {showDetail &&
              data.platforms.map((platform) => (
                <div key={platform.platform} className="border-t border-ink/10">
                  <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
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
                        <tr
                          key={post.post_id}
                          className="border-b border-ink/5 last:border-0"
                        >
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-ink">{post.title}</p>
                              <PublishPill
                                status={post.publish_status}
                                permalink={post.permalink}
                              />
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
              ))}
          </section>
        </>
      )}
    </div>
  );
}

function IntegrationsCard({
  campaignId,
  defaultTitle,
  defaultBody,
}: {
  campaignId: string;
  defaultTitle: string;
  defaultBody: string;
}) {
  const [title, setTitle] = useState(defaultTitle);
  const [body, setBody] = useState(defaultBody);
  const [linearKey, setLinearKey] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [sending, setSending] = useState<"linear" | "webhook" | null>(null);
  const [result, setResult] = useState<IntegrationDispatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function send(target: "linear" | "webhook") {
    setSending(target);
    setResult(null);
    setError(null);
    try {
      const res = await dispatchIntegration({
        target,
        title,
        body,
        campaign_id: campaignId,
        url: target === "webhook" ? webhookUrl : undefined,
        api_key: target === "linear" ? linearKey : undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dispatch failed.");
    } finally {
      setSending(null);
    }
  }

  async function copyPayload() {
    const payload = JSON.stringify(
      { source: "reelmatrix", campaign_id: campaignId, title, body },
      null,
      2,
    );
    try {
      await navigator.clipboard.writeText(payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("Copy failed — select the summary text instead.");
    }
  }

  return (
    <section className="surface p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="eyebrow">Route wins to your stack</p>
        <button className="btn-line px-2.5 py-1 text-xs" onClick={copyPayload}>
          {copied ? "Copied ✓" : "Copy JSON payload"}
        </button>
      </div>
      <p className="mt-1 text-sm text-ink/60">
        Send this results recap where your team already works. Credentials are used
        once to deliver and never stored.
      </p>

      <div className="mt-3 grid gap-3">
        <input
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Recap title"
        />
        <textarea
          className="input min-h-[72px] font-mono text-[12px]"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-ink/10 bg-white/70 p-3">
          <p className="text-sm font-semibold text-ink">Linear</p>
          <p className="mt-0.5 text-[12px] text-ink/55">
            Creates a real issue in your first Linear team.
          </p>
          <div className="mt-2 flex gap-2">
            <input
              className="input px-3 py-2 text-[12px]"
              type="password"
              value={linearKey}
              onChange={(e) => setLinearKey(e.target.value)}
              placeholder="lin_api_… personal key"
            />
            <button
              className="btn-line shrink-0 px-3 py-2 text-xs"
              disabled={sending !== null || linearKey.trim() === ""}
              onClick={() => send("linear")}
            >
              {sending === "linear" ? "Creating…" : "Create issue"}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-ink/10 bg-white/70 p-3">
          <p className="text-sm font-semibold text-ink">Webhook</p>
          <p className="mt-0.5 text-[12px] text-ink/55">
            Slack, Feishu, DingTalk, or any OA endpoint that accepts JSON.
          </p>
          <div className="mt-2 flex gap-2">
            <input
              className="input px-3 py-2 text-[12px]"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://hooks.example.com/…"
            />
            <button
              className="btn-line shrink-0 px-3 py-2 text-xs"
              disabled={sending !== null || webhookUrl.trim() === ""}
              onClick={() => send("webhook")}
            >
              {sending === "webhook" ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {result.detail}{" "}
          {result.permalink && (
            <a
              href={result.permalink}
              target="_blank"
              rel="noreferrer"
              className="font-semibold underline"
            >
              View ↗
            </a>
          )}
        </p>
      )}
      {error && (
        <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </section>
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
