"use client";

import type { PerformanceData } from "@/lib/teamApi";

function pct(n: number, d: number): string {
  return d > 0 ? `${((n / d) * 100).toFixed(1)}%` : "—";
}

export function PerformanceView({ data }: { data: PerformanceData }) {
  const totals = data.totals;
  const impressions = totals.impressions ?? 0;
  const clicks = totals.clicks ?? 0;
  const signups = totals.signups ?? 0;

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
        {data.note}
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
        <Tile label="Assets" value={String(data.rows.length)} />
      </div>

      <div className="overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-soft">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink/10 text-left font-mono text-[11px] text-ink/50">
              <th className="px-4 py-2 font-normal">Asset</th>
              <th className="px-3 py-2 text-right font-normal">Impr.</th>
              <th className="px-3 py-2 text-right font-normal">Clicks</th>
              <th className="px-3 py-2 text-right font-normal">Signups</th>
              <th className="px-4 py-2 font-normal">UTM link</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.task_id} className="border-b border-ink/5 last:border-0">
                <td className="px-4 py-2.5">
                  <p className="font-semibold text-ink">{row.title}</p>
                  <p className="font-mono text-[11px] text-forest">
                    {row.channel} · {row.source}
                  </p>
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[12px]">
                  {row.impressions.toLocaleString()}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[12px]">
                  {row.clicks.toLocaleString()}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[12px] font-semibold text-forest">
                  {row.signups.toLocaleString()}
                </td>
                <td className="max-w-xs px-4 py-2.5">
                  <a
                    href={row.utm_url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate font-mono text-[11px] text-ink/50 hover:text-ink hover:underline"
                    title={row.utm_url}
                  >
                    {row.utm_url}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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
