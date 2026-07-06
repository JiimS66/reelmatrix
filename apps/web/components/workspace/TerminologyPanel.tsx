"use client";

import { useState } from "react";

import { createTerm, deleteTerm, type BrandTermItem } from "@/lib/teamApi";

const TYPE_LABEL: Record<string, string> = {
  approved: "Approved",
  avoid: "Avoid",
  use_carefully: "Use carefully",
};

const TYPE_CLS: Record<string, string> = {
  approved: "border-emerald-200 bg-emerald-50 text-emerald-700",
  avoid: "border-red-200 bg-red-50 text-red-700",
  use_carefully: "border-amber-200 bg-amber-50 text-amber-700",
};

export function TerminologyPanel({
  terms,
  currentMemberId,
  isLead,
  onChanged,
  onError,
}: {
  terms: BrandTermItem[];
  currentMemberId: string;
  isLead: boolean;
  onChanged: () => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const [term, setTerm] = useState("");
  const [type, setType] = useState("avoid");
  const [replacement, setReplacement] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    if (!term.trim()) return;
    setBusy(true);
    try {
      await createTerm(currentMemberId, {
        term: term.trim(),
        term_type: type,
        replacement: type === "avoid" ? replacement.trim() || null : null,
      });
      setTerm("");
      setReplacement("");
      await onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not add the term.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    try {
      await deleteTerm(currentMemberId, id);
      await onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not delete the term.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface space-y-3 p-4">
      <div>
        <p className="tlabel">Brand terminology</p>
        <p className="mt-0.5 text-sm text-ink/60">
          Typed terms checked on every post — avoid terms suggest a swap, use-carefully
          terms get a double-check.
        </p>
      </div>

      {isLead && (
        <div className="flex flex-wrap items-end gap-2">
          <input
            className="field max-w-[10rem]"
            value={term}
            placeholder="term"
            onChange={(e) => setTerm(e.target.value)}
          />
          <select className="field max-w-[9rem]" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="avoid">Avoid</option>
            <option value="use_carefully">Use carefully</option>
            <option value="approved">Approved</option>
          </select>
          {type === "avoid" && (
            <input
              className="field max-w-[10rem]"
              value={replacement}
              placeholder="use instead (optional)"
              onChange={(e) => setReplacement(e.target.value)}
            />
          )}
          <button className="btn-dark" disabled={busy || !term.trim()} onClick={add}>
            Add
          </button>
        </div>
      )}

      {terms.length === 0 ? (
        <p className="text-sm text-ink/55">No terms yet.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {terms.map((t) => (
            <li
              key={t.id}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-sm ${
                TYPE_CLS[t.term_type] ?? "border-ink/10 bg-canvas text-ink/70"
              }`}
            >
              <span className="font-mono text-[11px] uppercase opacity-70">
                {TYPE_LABEL[t.term_type] ?? t.term_type}
              </span>
              <span className="font-medium">{t.term}</span>
              {t.replacement && <span className="opacity-70">→ {t.replacement}</span>}
              {isLead && (
                <button
                  className="ml-0.5 opacity-50 hover:opacity-100"
                  title="Remove"
                  disabled={busy}
                  onClick={() => remove(t.id)}
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
