"use client";

import { useState } from "react";

import { importHistorical, ingestBrandKnowledge } from "@/lib/teamApi";

/** Enterprise warm-start: import a customer's existing history + brand docs so the
 * flywheel, ICP, and brand knowledge start with real priors, not cold. */
export function OnboardingPanel({
  memberId,
  canManage,
  onChanged,
}: {
  memberId: string;
  canManage: boolean;
  onChanged: () => void;
}) {
  const [rowsText, setRowsText] = useState("");
  const [docText, setDocText] = useState("");
  const [busy, setBusy] = useState(false);
  const [imported, setImported] = useState<number | null>(null);
  const [priors, setPriors] = useState<string[]>([]);
  const [brandVp, setBrandVp] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (!canManage) return null;

  async function doImport() {
    let rows: unknown;
    try {
      rows = JSON.parse(rowsText);
    } catch {
      setErr("Historical data must be a JSON array of rows.");
      return;
    }
    if (!Array.isArray(rows)) {
      setErr("Historical data must be a JSON array.");
      return;
    }
    setErr(null);
    setBusy(true);
    try {
      const r = await importHistorical(memberId, rows as Record<string, unknown>[]);
      setImported(r.imported);
      setPriors(r.insights.priors);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function doBrand() {
    if (!docText.trim()) return;
    setBusy(true);
    try {
      const r = await ingestBrandKnowledge(memberId, docText.trim());
      setBrandVp(r.draft.value_proposition);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <p className="tlabel">Onboard — warm-start from your existing world</p>
      <p className="mt-0.5 text-sm text-ink/55">
        Import history → the flywheel &amp; ICP start with real priors, not cold-start.
      </p>
      {err && <p className="mt-2 text-[12px] text-coral">{err}</p>}
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="tlabel">Historical content + performance (JSON rows)</p>
          <textarea
            className="mt-1 w-full rounded-lg border border-ink/15 bg-white px-3 py-1.5 font-mono text-[11px]"
            rows={4}
            placeholder='[{"title":"…","content":"…","channel":"LinkedIn","segment":"Eng","impressions":1000,"clicks":200,"conversions":80}]'
            value={rowsText}
            onChange={(e) => setRowsText(e.target.value)}
          />
          <button
            className="btn-line mt-1.5 px-3 py-1 text-xs"
            disabled={busy || !rowsText.trim()}
            onClick={doImport}
          >
            Import history
          </button>
          {imported !== null && (
            <p className="mt-1.5 text-[12px] text-forest">
              ✓ {imported} posts imported — flywheel warm-started.
            </p>
          )}
          {priors.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {priors.slice(0, 2).map((p, i) => (
                <li key={i} className="text-[11px] text-ink/55">
                  — {p}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="tlabel">Brand docs / guidelines (paste text)</p>
          <textarea
            className="mt-1 w-full rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-[12px]"
            rows={4}
            placeholder="Paste brand guidelines, positioning, or about-us copy…"
            value={docText}
            onChange={(e) => setDocText(e.target.value)}
          />
          <button
            className="btn-line mt-1.5 px-3 py-1 text-xs"
            disabled={busy || !docText.trim()}
            onClick={doBrand}
          >
            Extract brand
          </button>
          {brandVp && (
            <p className="mt-1.5 text-[12px] text-forest">
              ✓ Applied — value prop: &ldquo;{brandVp}&rdquo;
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
