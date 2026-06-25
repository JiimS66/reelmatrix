"use client";

import { useEffect, useState } from "react";

import {
  getBrand,
  type Atom,
  type BrandProfile,
  type BrandTermItem,
} from "@/lib/teamApi";

import { TerminologyPanel } from "./TerminologyPanel";
import { ATOM_KIND_LABEL, cap } from "./primitives";

export function BrandHub({
  terms,
  atoms,
  currentMemberId,
  isLead,
  onChanged,
  onError,
}: {
  terms: BrandTermItem[];
  atoms: Atom[];
  currentMemberId: string;
  isLead: boolean;
  onChanged: () => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  useEffect(() => {
    getBrand(currentMemberId)
      .then(setBrand)
      .catch(() => {});
  }, [currentMemberId]);

  return (
    <div className="space-y-5">
      {brand && (
        <div className="surface p-4">
          <p className="tlabel">Brand voice — the backbone every channel renders from</p>
          {brand.voice && <p className="mt-1.5 text-sm text-ink/80">{brand.voice}</p>}
          {brand.tone_rules.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {brand.tone_rules.map((r) => (
                <li key={r} className="chip">
                  {r}
                </li>
              ))}
            </ul>
          )}
          {brand.proof_points.length > 0 && (
            <div className="mt-3">
              <p className="tlabel">Proof points · the truth library</p>
              <ul className="mt-1.5 space-y-1.5">
                {brand.proof_points.map((p, i) => (
                  <li
                    key={i}
                    className="rounded-lg border border-emerald-200 bg-emerald-50/40 px-2.5 py-1.5 text-sm text-ink/80"
                  >
                    {String(p.claim ?? "")}
                    {p.source && (
                      <a
                        href={String(p.source)}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-1.5 font-mono text-[10px] text-forest hover:underline"
                      >
                        🔗 source
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <TerminologyPanel
        terms={terms}
        currentMemberId={currentMemberId}
        isLead={isLead}
        onChanged={onChanged}
        onError={onError}
      />

      <AtomsGrid atoms={atoms} />
    </div>
  );
}

function AtomsGrid({ atoms }: { atoms: Atom[] }) {
  if (atoms.length === 0) {
    return (
      <p className="surface p-6 text-sm text-ink/60">
        No reusable atoms yet. Approve posts and hooks, headlines, and CTAs land here
        for the next campaign.
      </p>
    );
  }
  const byKind = atoms.reduce<Record<string, Atom[]>>((acc, atom) => {
    (acc[atom.kind] ||= []).push(atom);
    return acc;
  }, {});
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Object.entries(byKind).map(([kind, items]) => (
        <div key={kind} className="surface p-4">
          <p className="tlabel">{ATOM_KIND_LABEL[kind] ?? cap(kind)}</p>
          <ul className="mt-2 space-y-2">
            {items.map((atom) => (
              <li
                key={atom.id}
                className="rounded-lg border border-ink/10 bg-canvas p-2.5 text-sm text-ink"
              >
                {atom.text}
                {atom.tags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {atom.tags.map((tag) => (
                      <span key={tag} className="font-mono text-[10px] text-forest">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
