"use client";

import { useEffect, useRef, useState } from "react";

export interface Command {
  id: string;
  label: string;
  group?: string;
  run: () => void;
}

/** Phase 15 — a keyboard-first command palette (⌘K / Ctrl-K). Hand-rolled, no dependency.
 * The density-reliever for a feature-rich app: jump anywhere without hunting through tabs. */
export function CommandPalette({ commands }: { commands: Command[] }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQ("");
      setIdx(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  if (!open) return null;

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(q.toLowerCase()),
  );
  function exec(c: Command) {
    c.run();
    setOpen(false);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 pt-[15vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-ink/15 bg-canvas shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="w-full border-b border-ink/10 bg-transparent px-4 py-3 text-sm outline-none"
          placeholder="Jump to…  (⌘K)"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setIdx(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setIdx((i) => Math.min(i + 1, filtered.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setIdx((i) => Math.max(i - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              if (filtered[idx]) exec(filtered[idx]);
            }
          }}
        />
        <ul className="max-h-72 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <li className="px-4 py-2 text-sm text-ink/40">No matches</li>
          ) : (
            filtered.map((c, i) => (
              <li key={c.id}>
                <button
                  className={`flex w-full items-center gap-2 px-4 py-2 text-left text-sm ${
                    i === idx ? "bg-forest/10 text-ink" : "text-ink/70"
                  }`}
                  onMouseEnter={() => setIdx(i)}
                  onClick={() => exec(c)}
                >
                  {c.group && (
                    <span className="font-mono text-[10px] text-ink/40">{c.group}</span>
                  )}
                  <span>{c.label}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
