"use client";

import { useEffect, useState } from "react";

import {
  listChannels,
  updateChannel,
  upsertChannel,
  type ChannelProfile,
} from "@/lib/teamApi";

/** The channel registry: which platforms this brand ACTUALLY operates. The
 * planner only assigns posts to active channels, and the copywriter reads each
 * channel's handle/audience note + its recent post history — this is what keeps
 * per-platform content consistent and continuous. */
export function ChannelsPanel({
  memberId,
  canManage,
}: {
  memberId: string;
  canManage: boolean;
}) {
  const [channels, setChannels] = useState<ChannelProfile[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState({ handle: "", audience_note: "", cadence: "" });
  const [adding, setAdding] = useState(false);
  const [newPlatform, setNewPlatform] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listChannels(memberId)
      .then(setChannels)
      .catch(() => {});
  }, [memberId]);

  async function run(fn: () => Promise<ChannelProfile[]>) {
    setBusy(true);
    setError(null);
    try {
      setChannels(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <p className="tlabel">Channels</p>
          <p className="font-mono text-[11px] text-ink/45">
            the AI drafts only where you actually publish
          </p>
        </div>
        {canManage && (
          <button
            className="btn-line px-2.5 py-1 text-xs"
            onClick={() => setAdding((v) => !v)}
          >
            + Add channel
          </button>
        )}
      </div>

      {adding && (
        <div className="mt-3 flex flex-wrap gap-2 rounded-lg bg-ink/[0.04] p-3">
          <input
            className="field flex-1 py-1.5 text-xs"
            placeholder="Platform name, e.g. YouTube"
            value={newPlatform}
            onChange={(e) => setNewPlatform(e.target.value)}
          />
          <button
            className="btn-dark px-3 py-1.5 text-xs"
            disabled={busy || !newPlatform.trim()}
            onClick={() =>
              run(() => upsertChannel(memberId, { platform: newPlatform.trim() })).then(
                () => {
                  setNewPlatform("");
                  setAdding(false);
                },
              )
            }
          >
            Add
          </button>
        </div>
      )}

      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {channels.map((c) => (
          <li
            key={c.id}
            className={`rounded-xl border p-3 ${
              c.active
                ? "border-ink/10 bg-white"
                : "border-dashed border-ink/15 bg-canvas opacity-70"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-ink">{c.platform}</p>
              {canManage && (
                <button
                  className={`rounded-full px-2 py-0.5 font-mono text-[11px] transition ${
                    c.active
                      ? "bg-forest/10 text-forest hover:bg-forest/20"
                      : "bg-ink/10 text-ink/50 hover:bg-ink/20"
                  }`}
                  disabled={busy}
                  onClick={() =>
                    run(() => updateChannel(memberId, c.id, { active: !c.active }))
                  }
                  title={c.active ? "Pause: the AI stops drafting here" : "Activate"}
                >
                  {c.active ? "active" : "paused"}
                </button>
              )}
            </div>
            {editing === c.id ? (
              <div className="mt-2 space-y-1.5">
                <input
                  className="field w-full py-1 text-xs"
                  placeholder="@handle / URL"
                  value={draft.handle}
                  onChange={(e) => setDraft({ ...draft, handle: e.target.value })}
                />
                <input
                  className="field w-full py-1 text-xs"
                  placeholder="Audience note — who follows us here"
                  value={draft.audience_note}
                  onChange={(e) => setDraft({ ...draft, audience_note: e.target.value })}
                />
                <input
                  className="field w-full py-1 text-xs"
                  placeholder="Cadence, e.g. 2x/week"
                  value={draft.cadence}
                  onChange={(e) => setDraft({ ...draft, cadence: e.target.value })}
                />
                <div className="flex gap-2">
                  <button
                    className="btn-green px-2.5 py-1 text-xs"
                    disabled={busy}
                    onClick={() =>
                      run(() => updateChannel(memberId, c.id, draft)).then(() =>
                        setEditing(null),
                      )
                    }
                  >
                    Save
                  </button>
                  <button
                    className="btn-line px-2.5 py-1 text-xs"
                    onClick={() => setEditing(null)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-1.5 space-y-0.5">
                <p className="font-mono text-[11px] text-forest">{c.handle || "—"}</p>
                {c.audience_note && (
                  <p className="text-[12px] text-ink/55">{c.audience_note}</p>
                )}
                <div className="flex items-center justify-between">
                  <p className="font-mono text-[11px] text-ink/40">{c.cadence}</p>
                  {canManage && (
                    <button
                      className="font-mono text-[11px] text-ink/40 hover:text-ink"
                      onClick={() => {
                        setEditing(c.id);
                        setDraft({
                          handle: c.handle,
                          audience_note: c.audience_note,
                          cadence: c.cadence,
                        });
                      }}
                    >
                      edit
                    </button>
                  )}
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
