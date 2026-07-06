"use client";

import { useEffect, useState } from "react";

import { getBrand, type BrandProfile } from "@/lib/teamApi";

export interface Claim {
  claim: string;
  status: string; // source_backed | needs_validation
  source?: string | null;
}

export function ClaimCheckView({
  claims,
  onChange,
  currentMemberId,
  readOnly,
}: {
  claims: Claim[];
  onChange: (next: Claim[]) => void;
  currentMemberId: string;
  readOnly: boolean;
}) {
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  useEffect(() => {
    getBrand(currentMemberId)
      .then(setBrand)
      .catch(() => {});
  }, [currentMemberId]);

  const backed = claims.filter((c) => c.status === "source_backed").length;
  const pct = claims.length > 0 ? Math.round((backed / claims.length) * 100) : 0;

  const update = (i: number, patch: Partial<Claim>) =>
    onChange(claims.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  const remove = (i: number) => onChange(claims.filter((_, idx) => idx !== i));
  const add = (claim: Claim) => onChange([...claims, claim]);

  return (
    <div className="space-y-3">
      {/* Coverage */}
      <div className="rounded-lg border border-ink/10 bg-canvas p-2.5">
        <div className="flex items-center justify-between text-sm">
          <span className="tlabel">Fact-check coverage</span>
          <span className="font-mono text-[12px] text-ink/70">
            {backed}/{claims.length} verified
          </span>
        </div>
        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-ink/10">
          <div
            className={`h-full ${pct === 100 ? "bg-forest" : "bg-amber-400"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {claims.length === 0 && (
        <p className="text-sm text-ink/55">
          No claims yet. Add every funding, customer, user-count, or performance claim
          that needs a source before publishing.
        </p>
      )}

      <ul className="space-y-2">
        {claims.map((c, i) => {
          const verified = c.status === "source_backed";
          return (
            <li
              key={i}
              className={`rounded-xl border p-2.5 ${
                verified
                  ? "border-emerald-200 bg-emerald-50/40"
                  : "border-amber-200 bg-amber-50/40"
              }`}
            >
              <textarea
                className="field min-h-12 resize-y text-sm"
                value={c.claim}
                placeholder="The claim being made…"
                disabled={readOnly}
                onChange={(e) => update(i, { claim: e.target.value })}
              />
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={readOnly}
                  onClick={() =>
                    update(i, {
                      status: verified ? "needs_validation" : "source_backed",
                    })
                  }
                  className={`rounded-full px-2.5 py-1 font-mono text-[11px] ${
                    verified
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {verified ? "✓ Source-backed" : "⚠ Needs validation"}
                </button>
                <input
                  className="field flex-1"
                  value={c.source ?? ""}
                  placeholder="source URL"
                  disabled={readOnly}
                  onChange={(e) => update(i, { source: e.target.value })}
                />
                {!readOnly && (
                  <button
                    type="button"
                    className="px-1 text-ink/40 hover:text-red-600"
                    title="Remove"
                    onClick={() => remove(i)}
                  >
                    ×
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {!readOnly && (
        <button
          type="button"
          className="btn-line text-sm"
          onClick={() => add({ claim: "", status: "needs_validation", source: "" })}
        >
          + Add claim
        </button>
      )}

      {/* Approved proof points: click to drop in a pre-sourced claim */}
      {!readOnly && brand && brand.proof_points.length > 0 && (
        <div className="rounded-lg border border-ink/10 bg-canvas p-2.5">
          <p className="tlabel">Approved proof points</p>
          <p className="mt-0.5 text-[11px] text-ink/50">
            Click to add a verified, sourced claim.
          </p>
          <div className="mt-2 space-y-1.5">
            {brand.proof_points.map((p, i) => (
              <button
                key={i}
                type="button"
                onClick={() =>
                  add({
                    claim: String(p.claim ?? ""),
                    status: "source_backed",
                    source: p.source ?? "",
                  })
                }
                className="block w-full rounded-lg border border-ink/10 bg-white px-2.5 py-1.5 text-left text-sm hover:border-forest/40"
              >
                {String(p.claim ?? "")}
                {p.source && <span className="ml-1 font-mono text-[11px] text-forest">🔗</span>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
