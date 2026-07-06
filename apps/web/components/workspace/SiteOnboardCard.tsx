"use client";

import { useState } from "react";

import { onboardFromUrl, type OnboardFromUrlResult } from "@/lib/teamApi";

/** One-URL setup: paste the company site, get the channel registry prefilled
 * from its REAL social links and a brand-voice draft from the page text. Shown
 * on the cold-start screen and in the Brand tab. */
export function SiteOnboardCard({
  memberId,
  onDone,
}: {
  memberId: string;
  onDone?: () => void;
}) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<OnboardFromUrlResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await onboardFromUrl(memberId, { url: url.trim(), apply: true });
      setResult(r);
      onDone?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the site.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <div className="flex items-baseline gap-2">
        <p className="tlabel">Set up from your website</p>
        <p className="font-mono text-[11px] text-ink/45">
          real social links → channels · page copy → brand draft
        </p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <input
          className="field min-w-64 flex-1"
          placeholder="yourcompany.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") run();
          }}
        />
        <button className="btn-dark" disabled={busy || !url.trim()} onClick={run}>
          {busy ? "Reading…" : "Prefill my workspace"}
        </button>
      </div>
      {result && (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          <p className="font-semibold">
            Done — {result.channels.length} channel
            {result.channels.length === 1 ? "" : "s"} detected, brand draft applied.
          </p>
          {result.channels.length > 0 && (
            <p className="mt-1 flex flex-wrap gap-1.5">
              {result.channels.map((c) => (
                <span
                  key={c.platform}
                  className="rounded-full bg-white/70 px-2 py-0.5 font-mono text-[11px]"
                  title={c.handle}
                >
                  {c.platform}
                </span>
              ))}
            </p>
          )}
          {result.draft.value_proposition && (
            <p className="mt-1 text-[12px] text-emerald-700">
              Draft value prop: “{result.draft.value_proposition}” — refine it in the
              Brand tab.
            </p>
          )}
        </div>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
