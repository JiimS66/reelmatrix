"use client";

import { useEffect, useState } from "react";

import {
  deleteSegment,
  getBrand,
  upsertSegment,
  type Atom,
  type BrandProfile,
  type BrandTermItem,
  type IcpSegment,
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
      <SegmentsPanel
        segments={brand?.segments ?? []}
        currentMemberId={currentMemberId}
        isLead={isLead}
        onChange={() => getBrand(currentMemberId).then(setBrand).catch(() => {})}
        onError={onError}
      />

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

function SegmentsPanel({
  segments,
  currentMemberId,
  isLead,
  onChange,
  onError,
}: {
  segments: IcpSegment[];
  currentMemberId: string;
  isLead: boolean;
  onChange: () => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [platforms, setPlatforms] = useState("");
  const [pains, setPains] = useState("");
  const [reach, setReach] = useState("");
  const [busy, setBusy] = useState(false);

  const split = (s: string) =>
    s.split(",").map((x) => x.trim()).filter(Boolean);

  async function add() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await upsertSegment(currentMemberId, {
        name: name.trim(),
        platforms: split(platforms),
        pain_points: split(pains),
        reach_tactics: split(reach),
      });
      setName("");
      setPlatforms("");
      setPains("");
      setReach("");
      setAdding(false);
      await onChange();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not save the segment.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(segName: string) {
    setBusy(true);
    try {
      await deleteSegment(currentMemberId, segName);
      await onChange();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not delete the segment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="tlabel">ICP — who we sell to</p>
          <p className="mt-0.5 text-sm text-ink/60">
            Segments with their platforms, pain points, and how to reach them. Each post
            is routed to a segment and leads with its pain.
          </p>
        </div>
        {isLead && (
          <button className="btn-line" onClick={() => setAdding((v) => !v)}>
            {adding ? "Cancel" : "+ Segment"}
          </button>
        )}
      </div>

      {adding && (
        <div className="mt-3 space-y-2 rounded-lg border border-forest/30 p-3">
          <input className="field" value={name} placeholder="Segment name" onChange={(e) => setName(e.target.value)} />
          <input className="field" value={platforms} placeholder="Platforms (comma-separated: LinkedIn, Email)" onChange={(e) => setPlatforms(e.target.value)} />
          <input className="field" value={pains} placeholder="Pain points (comma-separated)" onChange={(e) => setPains(e.target.value)} />
          <input className="field" value={reach} placeholder="Reach tactics (comma-separated)" onChange={(e) => setReach(e.target.value)} />
          <button className="btn-dark" disabled={busy || !name.trim()} onClick={add}>
            {busy ? "Saving…" : "Save segment"}
          </button>
        </div>
      )}

      {segments.length === 0 ? (
        <p className="mt-3 text-sm text-ink/55">No segments yet.</p>
      ) : (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {segments.map((s) => (
            <div key={s.name} className="rounded-xl border border-ink/10 bg-canvas p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="font-semibold text-ink">{s.name}</p>
                {isLead && (
                  <button className="text-ink/40 hover:text-red-600" disabled={busy} onClick={() => remove(s.name)} title="Remove">
                    ×
                  </button>
                )}
              </div>
              {s.profile && (
                <p className="mt-0.5 font-mono text-[11px] text-ink/45">{s.profile}</p>
              )}
              {s.platforms.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {s.platforms.map((p) => (
                    <span key={p} className="chip border-forest/30 text-forest">{p}</span>
                  ))}
                </div>
              )}
              {s.pain_points.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-sm text-ink/70">
                  {s.pain_points.map((p) => (
                    <li key={p}>· {p}</li>
                  ))}
                </ul>
              )}
              {(s.value_props?.length ?? 0) > 0 && (
                <p className="mt-1.5 text-[12px] text-emerald-700">
                  ✓ {s.value_props!.join(" · ")}
                </p>
              )}
              {s.reach_tactics.length > 0 && (
                <p className="mt-1.5 font-mono text-[11px] text-ink/45">
                  reach: {s.reach_tactics.join(" · ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
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
