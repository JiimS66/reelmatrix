"use client";

import { useCallback, useEffect, useState } from "react";

import { CalendarView } from "@/components/workspace/CalendarView";
import { HomeView } from "@/components/workspace/HomeView";
import { TaskDetailPanel } from "@/components/workspace/TaskDetailPanel";
import { TodoView } from "@/components/workspace/TodoView";
import {
  ATOM_KIND_LABEL,
  AssigneeChip,
  CheckBadges,
  KIND_LABEL,
  StatusBadge,
  cap,
  checkCount,
} from "@/components/workspace/primitives";
import {
  createCampaign,
  getBoard,
  getInbox,
  getSchedule,
  getTask,
  getTodo,
  listAtoms,
  listCampaigns,
  listMembers,
  reviewTask,
  runCampaign,
  TeamApiError,
  TESTSPRITE_BRIEF,
  type Atom,
  type Board,
  type Member,
  type ScheduleData,
  type Task,
  type TaskDetail,
  type TodoItem,
} from "@/lib/teamApi";

type View = "home" | "board" | "calendar" | "todo" | "atoms";

const VIEW_LABEL: Record<View, string> = {
  home: "Home",
  board: "Board",
  calendar: "Calendar",
  todo: "To-do",
  atoms: "Atom library",
};

function errMessage(error: unknown): string {
  if (error instanceof TeamApiError) return error.message;
  return error instanceof Error ? error.message : "Something went wrong.";
}

export default function Workspace() {
  const [members, setMembers] = useState<Member[]>([]);
  const [currentId, setCurrentId] = useState("");
  const [view, setView] = useState<View>("home");
  const [board, setBoard] = useState<Board | null>(null);
  const [inbox, setInbox] = useState<Task[]>([]);
  const [atoms, setAtoms] = useState<Atom[]>([]);
  const [schedule, setSchedule] = useState<ScheduleData | null>(null);
  const [todo, setTodo] = useState<TodoItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const current = members.find((m) => m.id === currentId) ?? null;
  const isLead = current?.role === "lead";
  const humans = members.filter((m) => m.kind === "human");

  useEffect(() => {
    listMembers()
      .then((ms) => {
        setMembers(ms);
        const lead = ms.find((m) => m.role === "lead" && m.kind === "human");
        setCurrentId(lead?.id ?? ms[0]?.id ?? "");
      })
      .catch((e) => setError(errMessage(e)));
  }, []);

  const refreshBoard = useCallback(async () => {
    if (!board || !currentId) return;
    try {
      setBoard(await getBoard(currentId, board.campaign.id));
    } catch (e) {
      setError(errMessage(e));
    }
  }, [board, currentId]);

  const refreshDetail = useCallback(async () => {
    if (!selectedId || !currentId) return;
    try {
      setDetail(await getTask(currentId, selectedId));
    } catch (e) {
      setError(errMessage(e));
    }
  }, [selectedId, currentId]);

  useEffect(() => {
    if (selectedId) refreshDetail();
    else setDetail(null);
  }, [selectedId, refreshDetail]);

  // On member change: load my inbox + the latest campaign so Home is populated.
  useEffect(() => {
    if (!currentId) return;
    getInbox(currentId).then(setInbox).catch((e) => setError(errMessage(e)));
    listCampaigns(currentId)
      .then((cs) => (cs.length > 0 ? getBoard(currentId, cs[0].id) : null))
      .then((b) => {
        if (b) setBoard(b);
      })
      .catch((e) => setError(errMessage(e)));
  }, [currentId]);

  useEffect(() => {
    if (!currentId) return;
    if (view === "atoms") {
      listAtoms(currentId).then(setAtoms).catch((e) => setError(errMessage(e)));
    }
    if (view === "todo") {
      getTodo(currentId).then(setTodo).catch((e) => setError(errMessage(e)));
    }
    if (view === "calendar" && board) {
      getSchedule(currentId, board.campaign.id)
        .then(setSchedule)
        .catch((e) => setError(errMessage(e)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, currentId, board?.campaign.id]);

  function openTaskOnBoard(id: string) {
    setSelectedId(id);
    setView("board");
  }

  async function onChanged() {
    await refreshBoard();
    await refreshDetail();
    if (currentId) {
      try {
        setInbox(await getInbox(currentId));
      } catch (e) {
        setError(errMessage(e));
      }
    }
  }

  async function approve(id: string) {
    if (!currentId) return;
    setBusy(true);
    try {
      await reviewTask(currentId, id, { action: "approve" });
      await onChanged();
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function bulkApprove(ids: string[]) {
    if (!currentId) return;
    setBusy(true);
    try {
      for (const id of ids) {
        await reviewTask(currentId, id, { action: "approve" });
      }
      await onChanged();
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function createAndRun() {
    if (!currentId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createCampaign(currentId, {
        name: "TestSprite launch",
        brief: TESTSPRITE_BRIEF,
        template: "general",
        event_name: "TestSprite v2 launch",
        event_date: "2026-07-31",
      });
      const ran = await runCampaign(currentId, created.campaign.id);
      setBoard(ran);
      setView("home");
      setSelectedId(null);
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function runAgain() {
    if (!board || !currentId) return;
    setBusy(true);
    try {
      setBoard(await runCampaign(currentId, board.campaign.id));
      await refreshDetail();
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function pickMember(id: string) {
    setCurrentId(id);
    setSelectedId(null);
    setView("home");
  }

  const boardTasks = board?.tasks ?? [];
  const needsYou = isLead
    ? boardTasks.filter(
        (t) =>
          t.status === "needs_review" ||
          t.status === "blocked" ||
          (t.assignee_id === currentId &&
            (t.status === "todo" || t.status === "in_progress")),
      )
    : inbox.filter((t) => t.status === "todo" || t.status === "in_progress");
  const needsYouCount = needsYou.length;

  return (
    <div className="min-h-screen gridbg">
      {/* Top bar */}
      <div className="bg-black text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-2.5">
          <div className="flex items-baseline gap-2">
            <span className="font-semibold tracking-tight">ReelMatrix</span>
            <span className="font-mono text-[11px] text-white/55">
              / Marketing Team OS
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-white/55">acting as</span>
            {humans.map((m) => (
              <button
                key={m.id}
                onClick={() => pickMember(m.id)}
                className={`rounded-full px-2.5 py-1 font-mono text-[11px] transition ${
                  m.id === currentId
                    ? "bg-forest text-white"
                    : "bg-white/10 text-white/70 hover:bg-white/20"
                }`}
              >
                {m.display_name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-6xl px-5 py-7">
        <header className="mb-6">
          <p className="tlabel">Human + AI marketing team</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
            {current ? `${current.display_name}'s workspace` : "Workspace"}
          </h1>
        </header>

        {/* Tabs */}
        <nav className="mb-5 flex flex-wrap gap-1.5">
          {(["home", "board", "calendar", "todo", "atoms"] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => {
                setView(v);
                setSelectedId(null);
              }}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-mono text-[12px] transition ${
                view === v
                  ? "bg-ink text-white"
                  : "border border-ink/10 bg-white text-ink/70 hover:text-ink"
              }`}
            >
              {VIEW_LABEL[v]}
              {v === "home" && needsYouCount > 0 && (
                <span
                  className={`rounded-full px-1.5 text-[10px] ${
                    view === v ? "bg-white/20 text-white" : "bg-forest text-white"
                  }`}
                >
                  {needsYouCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        {error && (
          <div
            role="alert"
            className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        {view === "atoms" ? (
          <AtomLibrary atoms={atoms} />
        ) : view === "calendar" ? (
          schedule ? (
            <CalendarView
              schedule={schedule}
              members={board?.members ?? members}
              onSelectTask={openTaskOnBoard}
            />
          ) : (
            <p className="surface p-6 text-sm text-ink/60">
              {board
                ? "Loading schedule…"
                : "Create a campaign with an event date to see the calendar."}
            </p>
          )
        ) : view === "todo" ? (
          <TodoView
            items={todo}
            members={board?.members ?? members}
            onSelectTask={openTaskOnBoard}
          />
        ) : (
          <div className="grid items-start gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            {/* Left: home queue or board list */}
            <div className="space-y-4">
              {view === "home" ? (
                <HomeView
                  role={isLead ? "lead" : "member"}
                  board={board}
                  inbox={inbox}
                  members={board?.members ?? members}
                  currentMemberId={currentId}
                  selectedId={selectedId}
                  busy={busy}
                  onSelect={setSelectedId}
                  onApprove={approve}
                  onBulkApprove={bulkApprove}
                  onStart={createAndRun}
                />
              ) : (
                <>
                  <BoardHeader
                    board={board}
                    isLead={!!isLead}
                    busy={busy}
                    onCreate={createAndRun}
                    onRun={runAgain}
                  />
                  {boardTasks.length > 0 && (
                    <ul className="space-y-2.5">
                      {boardTasks.map((task) => (
                        <li key={task.id}>
                          <TaskRow
                            task={task}
                            members={board?.members ?? members}
                            selected={task.id === selectedId}
                            onClick={() => setSelectedId(task.id)}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </div>

            {/* Right: detail */}
            <div className="lg:sticky lg:top-6">
              {detail ? (
                <div className="surface p-5">
                  <TaskDetailPanel
                    detail={detail}
                    members={board?.members ?? members}
                    currentMemberId={currentId}
                    onChanged={onChanged}
                    onError={(m) => setError(m)}
                  />
                </div>
              ) : (
                <div className="surface border-dashed p-6 text-sm text-ink/55">
                  Select a task to view, edit, review, reassign, or comment.
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function BoardHeader({
  board,
  isLead,
  busy,
  onCreate,
  onRun,
}: {
  board: Board | null;
  isLead: boolean;
  busy: boolean;
  onCreate: () => void;
  onRun: () => void;
}) {
  if (!board) {
    return (
      <div className="surface p-6">
        <p className="tlabel">Start</p>
        <h2 className="mt-1 text-lg font-semibold text-ink">Spin up a campaign</h2>
        <p className="mt-1 max-w-md text-sm text-ink/60">
          {isLead
            ? "Create the TestSprite launch and let the AI team draft the whole package."
            : "Only the lead can create a campaign. Switch to the lead to start one."}
        </p>
        {isLead && (
          <button className="btn-dark mt-4" disabled={busy} onClick={onCreate}>
            {busy ? "Drafting…" : "New TestSprite campaign →"}
          </button>
        )}
      </div>
    );
  }
  return (
    <div className="surface flex flex-wrap items-center justify-between gap-3 p-4">
      <div>
        <p className="tlabel">Campaign</p>
        <h2 className="mt-0.5 font-semibold text-ink">{board.campaign.name}</h2>
      </div>
      {isLead && (
        <button className="btn-line" disabled={busy} onClick={onRun}>
          {busy ? "Running…" : "Run AI ↻"}
        </button>
      )}
    </div>
  );
}

function TaskRow({
  task,
  members,
  selected,
  onClick,
}: {
  task: Task;
  members: Member[];
  selected: boolean;
  onClick: () => void;
}) {
  const issues = checkCount(task);
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-2xl border bg-white p-4 text-left transition ${
        selected
          ? "border-forest ring-2 ring-forest/15"
          : "border-ink/10 hover:border-ink/25"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="tlabel">{KIND_LABEL[task.kind] ?? task.kind}</span>
        <StatusBadge status={task.status} />
      </div>
      <p className="mt-1.5 font-semibold text-ink">{task.title}</p>
      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        <AssigneeChip members={members} id={task.assignee_id} />
        {issues > 0 && (
          <span className="font-mono text-[11px] text-amber-700">
            {issues} check issue{issues === 1 ? "" : "s"}
          </span>
        )}
      </div>
      <div className="mt-2">
        <CheckBadges task={task} />
      </div>
    </button>
  );
}

function AtomLibrary({ atoms }: { atoms: Atom[] }) {
  if (atoms.length === 0) {
    return (
      <p className="surface p-6 text-sm text-ink/60">
        No atoms yet. Approve assets and reusable hooks, headlines, and CTAs land
        here for the next campaign.
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
