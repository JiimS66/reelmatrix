"use client";

import { useEffect, useState } from "react";

import { getDeployment, type DeploymentStatus } from "@/lib/teamApi";

/** Enterprise deployment posture — the "can it run with nothing leaving our VPC?" answer:
 * profile, which providers run local vs cloud, and the active privacy gates. */
export function DeploymentCard({ memberId }: { memberId: string }) {
  const [d, setD] = useState<DeploymentStatus | null>(null);

  useEffect(() => {
    getDeployment(memberId)
      .then(setD)
      .catch(() => {});
  }, [memberId]);

  if (!d) return null;

  return (
    <div className="surface p-5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="tlabel">Deployment — data residency &amp; privacy</p>
          <p className="mt-0.5 text-sm text-ink/55">
            {d.data_leaves_environment
              ? "Cloud profile — egress allowed with PII + consent controls."
              : "On-prem — no data leaves the environment."}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 font-mono text-[11px] ${
            d.data_leaves_environment ? "bg-ink/10 text-ink/60" : "bg-forest text-white"
          }`}
        >
          {d.profile}
        </span>
      </div>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="tlabel">Providers</p>
          <ul className="mt-1 space-y-0.5">
            {Object.entries(d.providers).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2 text-[12px]">
                <span className="text-ink/60">{k}</span>
                <span className="font-mono text-ink/80">{v}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="tlabel">Privacy gates</p>
          <ul className="mt-1 space-y-0.5">
            {Object.entries(d.gates).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2 text-[12px]">
                <span className="text-ink/60">{k}</span>
                <span className="font-mono text-forest">
                  {v === true ? "on" : String(v)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
