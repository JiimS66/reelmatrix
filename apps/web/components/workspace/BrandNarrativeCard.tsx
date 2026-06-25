"use client";

import { useEffect, useState } from "react";

import { getNarrative, setNarrative } from "@/lib/teamApi";

/** Phase 7 — the always-on brand narrative (value proposition + messaging pillars) that
 * spans every campaign; the writers generate from it. */
export function BrandNarrativeCard({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [vp, setVp] = useState("");
  const [pillars, setPillars] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getNarrative(memberId)
      .then((n) => {
        setVp(n.value_proposition);
        setPillars(n.messaging_pillars.map((p) => p.name).join(", "));
      })
      .catch(() => {});
  }, [memberId]);

  async function save() {
    setBusy(true);
    try {
      const ps = pillars
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((name) => ({ name }));
      const n = await setNarrative(memberId, {
        value_proposition: vp,
        messaging_pillars: ps,
      });
      setVp(n.value_proposition);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <p className="tlabel">Brand narrative — the always-on messaging pyramid</p>
      <p className="mt-0.5 text-sm text-ink/55">
        Spans every campaign; the writers generate from it.
      </p>
      <div className="mt-3 space-y-2">
        <div>
          <p className="tlabel">Value proposition</p>
          <input
            className="mt-1 w-full rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
            disabled={!canManage}
            value={vp}
            onChange={(e) => setVp(e.target.value)}
            placeholder="The one promise above every campaign…"
          />
        </div>
        <div>
          <p className="tlabel">Messaging pillars (comma-separated)</p>
          <input
            className="mt-1 w-full rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
            disabled={!canManage}
            value={pillars}
            onChange={(e) => setPillars(e.target.value)}
            placeholder="Trust, Speed, Proof"
          />
        </div>
        {canManage && (
          <button
            className="btn-line px-3 py-1.5 text-xs"
            disabled={busy}
            onClick={save}
          >
            {saved ? "Saved ✓" : "Save narrative"}
          </button>
        )}
      </div>
    </div>
  );
}
