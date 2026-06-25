"use client";

import { useEffect, useState } from "react";

import {
  addProspect,
  enrichProspect,
  getProspects,
  sendProspect,
  type Prospect,
} from "@/lib/teamApi";

const STATUS_TONE: Record<string, string> = {
  new: "border border-ink/15 text-ink/45",
  enriched: "bg-ink/10 text-ink/60",
  sent: "bg-forest text-white",
  blocked: "bg-coral/20 text-coral",
};

/** Phase 10 — scaled but 1:1 outbound: waterfall-enrich, AI-personalize, policy-gate, and
 * deliverability-cap before a (mock) send. */
export function OutboundPanel({
  memberId,
  campaignId,
  canManage,
}: {
  memberId: string;
  campaignId: string;
  canManage: boolean;
}) {
  const [rows, setRows] = useState<Prospect[]>([]);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setRows(await getProspects(memberId, campaignId));
    } catch {
      /* surfaced elsewhere */
    }
  }
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memberId, campaignId]);

  async function add() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      setRows(await addProspect(memberId, campaignId, { name: name.trim(), domain: domain.trim() }));
      setName("");
      setDomain("");
    } finally {
      setBusy(false);
    }
  }
  async function act(fn: () => Promise<Prospect[]>) {
    setBusy(true);
    try {
      setRows(await fn());
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface p-5">
      <p className="tlabel">Outbound — scaled but 1:1 (enrich · personalize · guard)</p>
      <p className="mt-0.5 text-sm text-ink/55">
        Every line is policy-gated and deliverability-capped.
      </p>
      {canManage && (
        <div className="mt-3 flex gap-2">
          <input
            className="flex-1 rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
            placeholder="Prospect name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="w-40 rounded-lg border border-ink/15 bg-white px-3 py-1.5 text-sm"
            placeholder="domain.com"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          />
          <button
            className="btn-line px-3 py-1.5 text-xs"
            disabled={busy || !name.trim()}
            onClick={add}
          >
            Add
          </button>
        </div>
      )}
      {rows.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {rows.map((p) => (
            <li key={p.id} className="rounded-lg border border-ink/10 bg-canvas p-2.5">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-ink">{p.name}</span>
                {p.company && (
                  <span className="text-[12px] text-ink/45">· {p.company}</span>
                )}
                <span className="flex-1" />
                <span
                  className={`rounded-full px-1.5 text-[10px] ${
                    STATUS_TONE[p.status] ?? ""
                  }`}
                >
                  {p.status}
                </span>
                {canManage && p.status === "new" && (
                  <button
                    className="btn-line px-2 py-0.5 text-[11px]"
                    disabled={busy}
                    onClick={() => act(() => enrichProspect(memberId, p.id))}
                  >
                    Enrich
                  </button>
                )}
                {canManage && p.status === "enriched" && (
                  <button
                    className="btn-line px-2 py-0.5 text-[11px]"
                    disabled={busy}
                    onClick={() => act(() => sendProspect(memberId, p.id))}
                  >
                    Send
                  </button>
                )}
              </div>
              {p.personalized_line && (
                <p className="mt-1 text-[12px] text-ink/65">{p.personalized_line}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
