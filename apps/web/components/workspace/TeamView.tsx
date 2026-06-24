"use client";

import { useState } from "react";

import {
  createOrgMember,
  updateOrgMember,
  type OrgData,
  type OrgMember,
} from "@/lib/teamApi";

import { KIND_LABEL } from "./primitives";

interface Props {
  org: OrgData;
  currentMemberId: string;
  isLead: boolean;
  onChanged: () => void | Promise<void>;
  onError: (message: string) => void;
}

export function TeamView({ org, currentMemberId, isLead, onChanged, onError }: Props) {
  const [hiring, setHiring] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const roleTitle = (key: string | null): string =>
    org.agent_roles.find((r) => r.key === key)?.title ?? key ?? "";

  // Two-level org chart: roots (no in-roster manager) then their direct reports.
  const ids = new Set(org.members.map((m) => m.id));
  const roots = org.members.filter((m) => !m.reports_to || !ids.has(m.reports_to));
  const reportsOf = (id: string) => org.members.filter((m) => m.reports_to === id);

  async function afterChange() {
    setHiring(false);
    setEditingId(null);
    await onChanged();
  }

  function card(member: OrgMember) {
    if (editingId === member.id) {
      return (
        <MemberForm
          key={member.id}
          mode="edit"
          member={member}
          org={org}
          currentMemberId={currentMemberId}
          onDone={afterChange}
          onCancel={() => setEditingId(null)}
          onError={onError}
        />
      );
    }
    return (
      <MemberCard
        key={member.id}
        member={member}
        roleTitle={roleTitle}
        canEdit={isLead && member.id !== currentMemberId}
        onEdit={() => {
          setHiring(false);
          setEditingId(member.id);
        }}
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="surface flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <p className="tlabel">Org</p>
          <h2 className="mt-0.5 font-semibold text-ink">
            Your digital + human team
          </h2>
          <p className="mt-0.5 text-sm text-ink/60">
            Who handles what is configured here — work routes by each member&apos;s
            handled kinds.
          </p>
        </div>
        {isLead &&
          (hiring ? (
            <button className="btn-line" onClick={() => setHiring(false)}>
              Cancel
            </button>
          ) : (
            <button
              className="btn-dark"
              onClick={() => {
                setEditingId(null);
                setHiring(true);
              }}
            >
              + Hire AI employee
            </button>
          ))}
      </div>

      {hiring && (
        <MemberForm
          mode="hire"
          member={null}
          org={org}
          currentMemberId={currentMemberId}
          onDone={afterChange}
          onCancel={() => setHiring(false)}
          onError={onError}
        />
      )}

      <div className="space-y-4">
        {roots.map((root) => {
          const reports = reportsOf(root.id);
          return (
            <div key={root.id} className="space-y-2.5">
              {card(root)}
              {reports.length > 0 && (
                <div className="ml-4 space-y-2.5 border-l-2 border-ink/10 pl-4">
                  {reports.map((member) => card(member))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function KindTag({ kind }: { kind: "human" | "ai" }) {
  return (
    <span className="chip">
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          kind === "ai" ? "bg-forest" : "bg-ink"
        }`}
      />
      {kind === "ai" ? "AI" : "Human"}
    </span>
  );
}

function MemberCard({
  member,
  roleTitle,
  canEdit,
  onEdit,
}: {
  member: OrgMember;
  roleTitle: (key: string | null) => string;
  canEdit: boolean;
  onEdit: () => void;
}) {
  return (
    <div className="surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-ink">{member.display_name}</span>
            <KindTag kind={member.kind} />
            {member.kind === "ai" ? (
              <span className="tlabel">{roleTitle(member.agent_role)}</span>
            ) : (
              <span className="tlabel">{member.role === "lead" ? "Lead" : "Member"}</span>
            )}
          </div>
          {member.job_description && (
            <p className="mt-1.5 text-sm text-ink/65">{member.job_description}</p>
          )}
        </div>
        {canEdit && (
          <button className="btn-line shrink-0 px-3 py-1.5 text-xs" onClick={onEdit}>
            Configure
          </button>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {member.handles_kinds.length > 0 ? (
          member.handles_kinds.map((kind) => (
            <span key={kind} className="chip">
              {KIND_LABEL[kind] ?? kind}
            </span>
          ))
        ) : (
          <span className="font-mono text-[11px] text-ink/40">handles nothing yet</span>
        )}
        {member.kind === "ai" && member.provider && (
          <span className="chip border-forest/30 text-forest">
            {member.provider}
            {member.model ? ` · ${member.model}` : ""}
          </span>
        )}
      </div>
    </div>
  );
}

function HandlesPicker({
  taskKinds,
  selected,
  onToggle,
}: {
  taskKinds: string[];
  selected: string[];
  onToggle: (kind: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {taskKinds.map((kind) => {
        const on = selected.includes(kind);
        return (
          <button
            type="button"
            key={kind}
            onClick={() => onToggle(kind)}
            className={`rounded-full border px-2.5 py-1 font-mono text-[11px] transition ${
              on
                ? "border-forest bg-forest text-white"
                : "border-ink/15 bg-white text-ink/70 hover:border-ink/40"
            }`}
          >
            {KIND_LABEL[kind] ?? kind}
          </button>
        );
      })}
    </div>
  );
}

function MemberForm({
  mode,
  member,
  org,
  currentMemberId,
  onDone,
  onCancel,
  onError,
}: {
  mode: "hire" | "edit";
  member: OrgMember | null;
  org: OrgData;
  currentMemberId: string;
  onDone: () => void | Promise<void>;
  onCancel: () => void;
  onError: (message: string) => void;
}) {
  const isAI = mode === "hire" ? true : member?.kind === "ai";
  const [name, setName] = useState(member?.display_name ?? "");
  const [role, setRole] = useState(member?.agent_role ?? org.agent_roles[0]?.key ?? "");
  const [job, setJob] = useState(member?.job_description ?? "");
  const [handles, setHandles] = useState<string[]>(member?.handles_kinds ?? []);
  const [reportsTo, setReportsTo] = useState(
    member?.reports_to ?? (mode === "hire" ? currentMemberId : ""),
  );
  const [provider, setProvider] = useState(member?.provider ?? "mock");
  const [model, setModel] = useState(member?.model ?? "");
  const [busy, setBusy] = useState(false);

  const toggle = (kind: string) =>
    setHandles((prev) =>
      prev.includes(kind) ? prev.filter((k) => k !== kind) : [...prev, kind],
    );

  const managerOptions = org.members.filter((m) => m.id !== member?.id);

  async function save() {
    setBusy(true);
    try {
      if (mode === "hire") {
        await createOrgMember(currentMemberId, {
          display_name: name.trim(),
          role,
          job_description: job,
          handles_kinds: handles,
          reports_to: reportsTo || null,
          provider,
          model: model || null,
        });
      } else if (member) {
        await updateOrgMember(currentMemberId, member.id, {
          job_description: job,
          handles_kinds: handles,
          reports_to: reportsTo || undefined,
          ...(isAI ? { role, provider, model: model || null } : {}),
        });
      }
      await onDone();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not save the member.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface space-y-3 border-forest/30 p-4">
      <p className="tlabel">{mode === "hire" ? "Hire an AI employee" : `Configure ${member?.display_name}`}</p>

      {mode === "hire" && (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="font-mono text-[11px] text-ink/55">Name</span>
            <input
              className="field"
              value={name}
              placeholder="e.g. Social copywriter"
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="space-y-1">
            <span className="font-mono text-[11px] text-ink/55">Runs as agent</span>
            <select
              className="field"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {org.agent_roles.map((r) => (
                <option key={r.key} value={r.key}>
                  {r.title}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {mode === "edit" && isAI && (
        <label className="block space-y-1">
          <span className="font-mono text-[11px] text-ink/55">Runs as agent</span>
          <select className="field" value={role} onChange={(e) => setRole(e.target.value)}>
            {org.agent_roles.map((r) => (
              <option key={r.key} value={r.key}>
                {r.title}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="block space-y-1">
        <span className="font-mono text-[11px] text-ink/55">Job description</span>
        <input
          className="field"
          value={job}
          placeholder="What this employee owns"
          onChange={(e) => setJob(e.target.value)}
        />
      </label>

      <div className="space-y-1">
        <span className="font-mono text-[11px] text-ink/55">Handles task kinds</span>
        <HandlesPicker taskKinds={org.task_kinds} selected={handles} onToggle={toggle} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="font-mono text-[11px] text-ink/55">Reports to</span>
          <select
            className="field"
            value={reportsTo}
            onChange={(e) => setReportsTo(e.target.value)}
          >
            <option value="">— no manager —</option>
            {managerOptions.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </label>
        {isAI && (
          <label className="space-y-1">
            <span className="font-mono text-[11px] text-ink/55">Provider · model</span>
            <div className="flex gap-2">
              <input
                className="field"
                value={provider}
                placeholder="mock"
                onChange={(e) => setProvider(e.target.value)}
              />
              <input
                className="field"
                value={model}
                placeholder="model (optional)"
                onChange={(e) => setModel(e.target.value)}
              />
            </div>
          </label>
        )}
      </div>

      <div className="flex gap-2 pt-1">
        <button
          className="btn-dark"
          disabled={busy || (mode === "hire" && (!name.trim() || !role))}
          onClick={save}
        >
          {busy ? "Saving…" : mode === "hire" ? "Hire" : "Save"}
        </button>
        <button className="btn-line" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
