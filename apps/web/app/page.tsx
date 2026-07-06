"use client";

import { useCallback, useEffect, useState } from "react";

import { CalendarView } from "@/components/workspace/CalendarView";
import { StrategyAdvisorPanel } from "@/components/workspace/StrategyAdvisorPanel";
import { BrandHub } from "@/components/workspace/BrandHub";
import { ChannelsPanel } from "@/components/workspace/ChannelsPanel";
import { BrandNarrativeCard } from "@/components/workspace/BrandNarrativeCard";
import { IcpMarketPanel } from "@/components/workspace/IcpMarketPanel";
import { OnboardingPanel } from "@/components/workspace/OnboardingPanel";
import { PillarFunnelPanel } from "@/components/workspace/PillarFunnelPanel";
import { ContentPreview } from "@/components/workspace/ContentPreview";
import { EmployeePage } from "@/components/workspace/EmployeePage";
import { AgentInbox } from "@/components/workspace/AgentInbox";
import { CommandPalette } from "@/components/workspace/CommandPalette";
import { HomeView } from "@/components/workspace/HomeView";
import { LaunchTimeline } from "@/components/workspace/LaunchTimeline";
import { MonthCalendar } from "@/components/workspace/MonthCalendar";
import { ExperimentsPanel } from "@/components/workspace/ExperimentsPanel";
import { GrowthInsightsCard } from "@/components/workspace/GrowthInsightsCard";
import { BudgetOptimizerPanel } from "@/components/workspace/BudgetOptimizerPanel";
import { IncrementalityPanel } from "@/components/workspace/IncrementalityPanel";
import { OutboundPanel } from "@/components/workspace/OutboundPanel";
import { PerformanceView } from "@/components/workspace/PerformanceView";
import { TaskDetailPanel } from "@/components/workspace/TaskDetailPanel";
import { DeploymentCard } from "@/components/workspace/DeploymentCard";
import { EvalPanel } from "@/components/workspace/EvalPanel";
import { ReliabilityCard } from "@/components/workspace/ReliabilityCard";
import { TeamView } from "@/components/workspace/TeamView";
import { UsageCard } from "@/components/workspace/UsageCard";
import {
  AssigneeChip,
  CheckBadges,
  KIND_LABEL,
  ScoreBadge,
  StatusBadge,
  averageScore,
  checkCount,
  statusAccent,
  statusTint,
} from "@/components/workspace/primitives";
import {
  createCampaign,
  downloadCopyPack,
  draftFromTrend,
  getBoard,
  getLlmProviders,
  getInbox,
  getReviewQueue,
  getTrends,
  getFleet,
  getOrg,
  listTerms,
  getPerformance,
  getSchedule,
  getTask,
  listAtoms,
  listCampaigns,
  listMembers,
  publishCampaign,
  refreshTrends,
  reviewTask,
  runCampaign,
  syncAnalytics,
  TeamApiError,
  TESTSPRITE_BRIEF,
  type Atom,
  type Board,
  type BrandTermItem,
  type Campaign,
  type FleetAgent,
  type Member,
  type OrgData,
  type PerformanceData,
  type ScheduleData,
  type Task,
  type TaskDetail,
  type TodoItem,
  type TrendAngle,
} from "@/lib/teamApi";

// Object-centric navigation (OA/ERP style): the nav lists BUSINESS OBJECTS — my desk,
// projects, the brand, the team. Workflow stages live INSIDE a campaign (kanban columns),
// where they explain themselves; people and decisions float up to Home.
type View = "home" | "campaigns" | "brand" | "team";

const VIEW_LABEL: Record<View, string> = {
  home: "Home",
  campaigns: "Campaigns",
  brand: "Brand",
  team: "Team",
};

type CampTab = "board" | "calendar" | "results";

// The campaign pipeline as kanban columns — a task lives in exactly one.
const KANBAN_COLS = [
  { key: "plan", label: "Plan", hint: "ideation & planning" },
  { key: "draft", label: "Draft", hint: "the AI team is writing" },
  { key: "review", label: "In review", hint: "waiting on a human" },
  { key: "done", label: "Approved", hint: "ready to publish" },
] as const;
type ColKey = (typeof KANBAN_COLS)[number]["key"];

function kanbanColOf(t: Task): ColKey {
  if (t.status === "needs_review") return "review";
  if (t.kind === "ideation" || t.kind === "planning") return "plan";
  if (t.status === "done") return "done";
  return "draft";
}

function errMessage(error: unknown): string {
  if (error instanceof TeamApiError) return error.message;
  return error instanceof Error ? error.message : "Something went wrong.";
}

export default function Workspace() {
  const [members, setMembers] = useState<Member[]>([]);
  const [currentId, setCurrentId] = useState("");
  const [view, setView] = useState<View>("home");
  const [liveModel, setLiveModel] = useState<string | null>(null);

  // The "live on …" badge: which model actually powers the copilot right now.
  useEffect(() => {
    getLlmProviders()
      .then((ps) => {
        const d = ps.find((p) => p.is_default);
        if (!d) return;
        setLiveModel(
          d.provider_id === "mock" ? "mock (offline demo)" : `${d.display_name} · ${d.model_name}`,
        );
      })
      .catch(() => {});
  }, []);
  const [campaignList, setCampaignList] = useState<Campaign[]>([]);
  const [activeCampaignId, setActiveCampaignId] = useState<string | null>(null);
  const [campTab, setCampTab] = useState<CampTab>("board");
  const [wizard, setWizard] = useState(false); // the strategy co-creation wizard (circuit A)
  const [board, setBoard] = useState<Board | null>(null);
  const [inbox, setInbox] = useState<Task[]>([]);
  const [atoms, setAtoms] = useState<Atom[]>([]);
  const [terms, setTerms] = useState<BrandTermItem[]>([]);
  const [org, setOrg] = useState<OrgData | null>(null);
  const [fleet, setFleet] = useState<FleetAgent[]>([]);
  const [employeeId, setEmployeeId] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<ScheduleData | null>(null);
  const [trends, setTrends] = useState<TrendAngle[]>([]);
  const [reviewQueue, setReviewQueue] = useState<TodoItem[]>([]);
  const [performance, setPerformance] = useState<PerformanceData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const current = members.find((m) => m.id === currentId) ?? null;
  const isLead = current?.role === "lead";
  const humans = members.filter((m) => m.kind === "human");
  // Cold start: a tenant with no campaigns opens straight into "think it through".
  const showWizard = wizard || campaignList.length === 0;

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

  // The cross-campaign review queue feeds the lead's Home desk + the sidebar count.
  const refreshQueue = useCallback(async () => {
    if (!currentId) return;
    try {
      setReviewQueue(await getReviewQueue(currentId));
    } catch (e) {
      setError(errMessage(e));
    }
  }, [currentId]);

  useEffect(() => {
    if (selectedId) refreshDetail();
    else setDetail(null);
  }, [selectedId, refreshDetail]);

  // On member change: my inbox + the campaign roster; open the latest campaign's board.
  useEffect(() => {
    if (!currentId) return;
    getInbox(currentId).then(setInbox).catch((e) => setError(errMessage(e)));
    refreshQueue();
    listCampaigns(currentId)
      .then((cs) => {
        setCampaignList(cs);
        if (cs.length > 0) setActiveCampaignId((prev) => prev ?? cs[0].id);
      })
      .catch((e) => setError(errMessage(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId]);

  // The board follows the active campaign.
  useEffect(() => {
    if (!currentId || !activeCampaignId) {
      setBoard(null);
      return;
    }
    getBoard(currentId, activeCampaignId)
      .then(setBoard)
      .catch((e) => setError(errMessage(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId, activeCampaignId]);

  useEffect(() => {
    if (!currentId) return;
    if (view === "brand") {
      listAtoms(currentId).then(setAtoms).catch((e) => setError(errMessage(e)));
      listTerms(currentId).then(setTerms).catch((e) => setError(errMessage(e)));
    }
    if (view === "team") {
      getOrg(currentId).then(setOrg).catch((e) => setError(errMessage(e)));
      getFleet(currentId).then(setFleet).catch((e) => setError(errMessage(e)));
    }
    if (view === "campaigns" && campTab === "results" && board) {
      getPerformance(currentId, board.campaign.id)
        .then(setPerformance)
        .catch((e) => setError(errMessage(e)));
    }
    if (view === "campaigns" && campTab === "calendar" && board) {
      getTrends(currentId, board.campaign.id)
        .then(setTrends)
        .catch((e) => setError(errMessage(e)));
    }
    refreshQueue(); // keep the "Needs you" count live across views
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, campTab, currentId, board?.campaign.id]);

  // The schedule powers the member desk strip + the campaign Calendar tab.
  useEffect(() => {
    if (!currentId || !board) {
      setSchedule(null);
      return;
    }
    getSchedule(currentId, board.campaign.id)
      .then(setSchedule)
      .catch((e) => setError(errMessage(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId, board?.campaign.id]);

  function openTaskOnBoard(id: string) {
    setSelectedId(id);
    setView("campaigns");
    setCampTab("board");
  }

  async function onChanged() {
    await refreshBoard();
    await refreshDetail();
    await refreshQueue();
    if (currentId) {
      try {
        setInbox(await getInbox(currentId));
      } catch (e) {
        setError(errMessage(e));
      }
      if (board) {
        try {
          setSchedule(await getSchedule(currentId, board.campaign.id));
        } catch (e) {
          setError(errMessage(e));
        }
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
        review_assets: true,
        with_visuals: true,
      });
      const ran = await runCampaign(currentId, created.campaign.id);
      setBoard(ran);
      setActiveCampaignId(ran.campaign.id);
      setCampaignList(await listCampaigns(currentId));
      setView("campaigns");
      setCampTab("board");
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
    setEmployeeId(null);
    setWizard(false);
    setView("home");
  }

  const boardTasks = board?.tasks ?? [];

  // Shared master-detail: a task list (left) + the task detail (right).
  const detailColumn = (
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
  );

  // The lead's desk: every campaign's awaiting-review work in one place, grouped under
  // its campaign so a decision anywhere empties that row.
  function reviewPane(items: TodoItem[]) {
    const groups: { name: string; tasks: Task[] }[] = [];
    for (const it of items) {
      let g = groups.find((x) => x.name === it.campaign_name);
      if (!g) {
        g = { name: it.campaign_name, tasks: [] };
        groups.push(g);
      }
      g.tasks.push(it.task);
    }
    return (
      <div className="grid items-start gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-4">
          <p className="tlabel">
            Needs you — approvals &amp; fact-checks across every campaign
          </p>
          {groups.length > 0 ? (
            <div className="space-y-5">
              {groups.map((g) => (
                <div key={g.name} className="space-y-2">
                  <p className="font-mono text-[11px] uppercase tracking-wide text-ink/45">
                    {g.name}
                  </p>
                  <ul className="space-y-2.5">
                    {g.tasks.map((task) => (
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
                </div>
              ))}
            </div>
          ) : (
            <p className="surface p-6 text-sm text-ink/60">
              Nothing needs you across your campaigns — all caught up.
            </p>
          )}
        </div>
        {detailColumn}
      </div>
    );
  }

  // ---- Home: the role-aware desk. Lead = decisions; member = my tasks. ----
  const homePane = showWizard ? (
    <div className="space-y-4">
      {campaignList.length > 0 && (
        <button className="btn-line px-3 py-1.5 text-xs" onClick={() => setWizard(false)}>
          ← Back to my desk
        </button>
      )}
      <StrategyAdvisorPanel
        memberId={currentId}
        onOpenContent={(b) => {
          setBoard(b);
          setActiveCampaignId(b.campaign.id);
          setSelectedId(null);
          setWizard(false);
          setCampTab("board");
          setView("campaigns");
          listCampaigns(currentId).then(setCampaignList).catch(() => {});
        }}
      />
    </div>
  ) : (
    <div className="space-y-5">
      {/* Numbers before sentences: the desk's vitals, each one a shortcut. */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          {
            label: "Needs you",
            value: reviewQueue.length,
            accent: reviewQueue.length > 0,
            go: () => {
              setView("home");
              setWizard(false);
            },
          },
          {
            label: "Campaigns",
            value: campaignList.length,
            accent: false,
            go: () => {
              setView("campaigns");
              setActiveCampaignId(null);
            },
          },
          {
            label: "Scheduled posts",
            value: schedule
              ? schedule.tasks.filter((t) => t.kind === "asset" && t.due_date).length
              : "—",
            accent: false,
            go: () => {
              setView("campaigns");
              setCampTab("calendar");
            },
          },
          {
            label: "Approved",
            value: boardTasks.filter((t) => t.kind === "asset" && t.status === "done")
              .length,
            accent: false,
            go: () => {
              setView("campaigns");
              setCampTab("board");
            },
          },
        ].map((kpi) => (
          <button
            key={kpi.label}
            onClick={kpi.go}
            className="surface p-4 text-left transition hover:border-forest/40"
          >
            <p className="tlabel">{kpi.label}</p>
            <p
              className={`mt-1 font-mono text-2xl font-semibold ${
                kpi.accent ? "text-forest" : "text-ink"
              }`}
            >
              {kpi.value}
            </p>
          </button>
        ))}
      </div>
      <div className="surface flex flex-wrap items-center justify-between gap-3 p-5">
        <div>
          <p className="tlabel">Start something</p>
          <p className="mt-1 max-w-lg text-sm text-ink/65">
            One sentence in, first drafts out.
          </p>
        </div>
        <button className="btn-dark" onClick={() => setWizard(true)}>
          ✨ New campaign from an idea
        </button>
      </div>
      {isLead ? (
        <>
          <AgentInbox memberId={currentId} canManage={!!isLead} />
          {reviewPane(reviewQueue)}
        </>
      ) : (
        <HomeView
          role="member"
          board={board}
          schedule={schedule}
          inbox={inbox}
          members={board?.members ?? members}
          currentMemberId={currentId}
          selectedId={selectedId}
          detail={detail}
          busy={busy}
          onSelect={setSelectedId}
          onApprove={approve}
          onBulkApprove={bulkApprove}
          onStart={createAndRun}
          onChanged={onChanged}
          onError={(m) => setError(m)}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );

  // ---- Campaigns: the project list, and inside a project the pipeline kanban. ----
  const activeCampaign = campaignList.find((c) => c.id === activeCampaignId) ?? null;
  const campaignsPane =
    !activeCampaign || !board ? (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="tlabel">Campaigns — every project in one place</p>
          <div className="flex gap-2">
            <button
              className="btn-line text-xs"
              onClick={() => {
                setView("home");
                setWizard(true);
              }}
            >
              ✨ New from an idea
            </button>
            {isLead && (
              <button className="btn-dark text-xs" disabled={busy} onClick={createAndRun}>
                {busy ? "Drafting…" : "New TestSprite campaign"}
              </button>
            )}
          </div>
        </div>
        {campaignList.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {campaignList.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  setActiveCampaignId(c.id);
                  setSelectedId(null);
                  setCampTab("board");
                }}
                className="surface p-4 text-left transition hover:border-forest/40"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="tlabel">{c.template}</span>
                  <span className="font-mono text-[11px] text-ink/45">{c.status}</span>
                </div>
                <p className="mt-1.5 font-semibold leading-snug text-ink">{c.name}</p>
                {c.event_date && (
                  <p className="mt-1 text-xs text-ink/50">Event: {c.event_date}</p>
                )}
              </button>
            ))}
          </div>
        ) : (
          <p className="surface p-6 text-sm text-ink/60">
            No campaigns yet — start one from an idea and the AI team drafts the rest.
          </p>
        )}
      </div>
    ) : (
      <div className="space-y-5">
        {/* Campaign header: back · name · score · run · tabs */}
        <div className="surface flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-center gap-3">
            <button
              className="btn-line px-2.5 py-1 text-xs"
              onClick={() => {
                setActiveCampaignId(null);
                setSelectedId(null);
              }}
              title="All campaigns"
            >
              ←
            </button>
            <div>
              <p className="tlabel">Campaign</p>
              <h2 className="mt-0.5 font-semibold text-ink">{board.campaign.name}</h2>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {averageScore(board.tasks) !== null && (
              <div className="text-right">
                <p className="tlabel">Avg score</p>
                <p
                  className={`font-mono text-lg font-semibold ${
                    (averageScore(board.tasks) ?? 0) >= 85
                      ? "text-forest"
                      : (averageScore(board.tasks) ?? 0) >= 60
                        ? "text-amber-700"
                        : "text-red-600"
                  }`}
                >
                  {averageScore(board.tasks)}
                </p>
              </div>
            )}
            {isLead && (
              <button className="btn-line" disabled={busy} onClick={runAgain}>
                {busy ? "Running…" : "Run AI ↻"}
              </button>
            )}
            <button
              className="btn-line"
              title="Approved posts as per-platform Markdown + tracking links, ready to publish"
              onClick={async () => {
                try {
                  await downloadCopyPack(currentId, board.campaign.id);
                } catch (e) {
                  setError(errMessage(e));
                }
              }}
            >
              ⇩ Copy pack
            </button>
            <div className="flex rounded-lg border border-ink/15 p-0.5">
              {(["board", "calendar", "results"] as CampTab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setCampTab(t)}
                  className={`rounded-md px-3 py-1 text-xs transition ${
                    campTab === t ? "bg-ink text-white" : "text-ink/60 hover:text-ink"
                  }`}
                >
                  {t === "board" ? "Board" : t === "calendar" ? "Calendar" : "Results"}
                </button>
              ))}
            </div>
          </div>
        </div>

        {campTab === "board" ? (
          <div className="space-y-5">
            {/* The launch schedule as channel swimlanes — and the object that
                syncs into the customer's OA (Linear). */}
            {schedule && (
              <LaunchTimeline
                schedule={schedule}
                memberId={currentId}
                canSync={!!isLead}
                onSelectTask={setSelectedId}
              />
            )}
            {/* The pipeline, as columns — each card carries who owns it (human or AI). */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {KANBAN_COLS.map((col) => {
                const items = boardTasks.filter((t) => kanbanColOf(t) === col.key);
                return (
                  <div key={col.key} className="rounded-xl bg-ink/[0.04] p-2.5">
                    <p className="tlabel px-1">
                      {col.label} <span className="text-ink/35">· {items.length}</span>
                    </p>
                    <p className="px-1 text-[11px] text-ink/40">{col.hint}</p>
                    <ul className="mt-2 space-y-2">
                      {items.map((t) => (
                        <li key={t.id}>
                          <KanbanCard
                            task={t}
                            members={board.members}
                            selected={t.id === selectedId}
                            onClick={() => setSelectedId(t.id)}
                          />
                        </li>
                      ))}
                    </ul>
                    {items.length === 0 && (
                      <p className="px-1 py-3 text-xs text-ink/35">—</p>
                    )}
                  </div>
                );
              })}
            </div>
            {selectedId && detailColumn}
          </div>
        ) : campTab === "calendar" ? (
          schedule ? (
            <div className="space-y-5">
              <MonthCalendar schedule={schedule} onSelectTask={openTaskOnBoard} />
              <CalendarView
                schedule={schedule}
                members={board.members}
                onSelectTask={openTaskOnBoard}
                canRefresh={!!isLead}
                angles={trends}
                onRefreshTrends={async () => {
                  if (!currentId) return;
                  try {
                    await refreshTrends(currentId, board.campaign.id);
                    setSchedule(await getSchedule(currentId, board.campaign.id));
                    setTrends(await getTrends(currentId, board.campaign.id));
                  } catch (e) {
                    setError(errMessage(e));
                  }
                }}
                onDraftAngle={async (angle, channel) => {
                  if (!currentId) return;
                  try {
                    setBoard(
                      await draftFromTrend(currentId, board.campaign.id, { angle, channel }),
                    );
                    setSchedule(await getSchedule(currentId, board.campaign.id));
                  } catch (e) {
                    setError(errMessage(e));
                  }
                }}
              />
              <ContentPreview tasks={schedule.tasks} />
            </div>
          ) : (
            <p className="surface p-6 text-sm text-ink/60">Loading schedule…</p>
          )
        ) : (
          <div className="space-y-5">
            {performance ? (
              <PerformanceView
                data={performance}
                canSync={!!isLead}
                onSync={async () => {
                  if (!currentId) return;
                  try {
                    setPerformance(await syncAnalytics(currentId, board.campaign.id));
                  } catch (e) {
                    setError(errMessage(e));
                  }
                }}
                onPublish={async () => {
                  if (!currentId) return;
                  try {
                    setPerformance(await publishCampaign(currentId, board.campaign.id));
                  } catch (e) {
                    setError(errMessage(e));
                  }
                }}
              />
            ) : (
              <p className="surface p-6 text-sm text-ink/60">Loading results…</p>
            )}
            <GrowthInsightsCard memberId={currentId} canLearn={!!isLead} />
            <ExperimentsPanel
              memberId={currentId}
              campaignId={board.campaign.id}
              canManage={!!isLead}
            />
            <PillarFunnelPanel
              memberId={currentId}
              campaignId={board.campaign.id}
              canManage={!!isLead}
              onChanged={onChanged}
            />
            <IncrementalityPanel memberId={currentId} canManage={!!isLead} />
            <BudgetOptimizerPanel memberId={currentId} canManage={!!isLead} />
            <OutboundPanel
              memberId={currentId}
              campaignId={board.campaign.id}
              canManage={!!isLead}
            />
          </div>
        )}
      </div>
    );

  return (
    <div className="min-h-screen gridbg">
      {/* Top bar */}
      <div className="bg-black text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-2.5">
          <div className="flex items-baseline gap-2">
            <span className="font-semibold tracking-tight">ReelMatrix</span>
            <span className="font-mono text-[11px] text-white/55">
              / Digital Marketing Copilot
            </span>
          </div>
          <div className="flex items-center gap-2">
            {liveModel && (
              <span
                className="mr-1 rounded-full border border-white/20 px-2.5 py-1 font-mono text-[11px] text-white/70"
                title="The live LLM behind the copilot — swappable by config (mock / OpenAI / Qwen / local)"
              >
                <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-forest align-middle" />
                live on {liveModel}
              </span>
            )}
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

      <main className="mx-auto max-w-7xl px-5 py-7">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            {current ? `${current.display_name}'s workspace` : "Workspace"}
          </h1>
        </header>

        <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
          <aside className="w-full shrink-0 lg:w-44">
            {!!isLead && reviewQueue.length > 0 && (
              <button
                onClick={() => {
                  setView("home");
                  setWizard(false);
                  setSelectedId(null);
                }}
                className="mb-3 w-full rounded-lg border border-forest/25 bg-forest/10 px-3 py-2 text-left transition hover:bg-forest/15"
              >
                <p className="tlabel text-forest/80">Needs you</p>
                <p className="font-mono text-xl font-semibold leading-tight text-forest">
                  {reviewQueue.length}
                </p>
              </button>
            )}
            {/* Sidebar — business objects, not workflow stages */}
            <nav className="flex flex-row flex-wrap gap-1 lg:flex-col">
              {(["home", "campaigns", "brand", "team"] as View[]).map((v) => (
                <button
                  key={v}
                  onClick={() => {
                    setView(v);
                    setWizard(false);
                    setSelectedId(null);
                    setEmployeeId(null);
                  }}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-left text-[13px] transition lg:w-full ${
                    view === v
                      ? "bg-ink text-white"
                      : "text-ink/70 hover:bg-ink/5 hover:text-ink"
                  }`}
                >
                  {VIEW_LABEL[v]}
                  {v === "home" && !!isLead && reviewQueue.length > 0 && (
                    <span
                      className={`rounded-full px-1.5 text-[11px] ${
                        view === v ? "bg-white/20 text-white" : "bg-forest text-white"
                      }`}
                    >
                      {reviewQueue.length}
                    </span>
                  )}
                  {v === "campaigns" && campaignList.length > 0 && (
                    <span
                      className={`rounded-full px-1.5 text-[11px] ${
                        view === v ? "bg-white/20 text-white" : "bg-ink/10 text-ink/60"
                      }`}
                    >
                      {campaignList.length}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </aside>

          <div className="min-w-0 flex-1">
            {error && (
              <div
                role="alert"
                className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700"
              >
                {error}
              </div>
            )}

            {view === "team" ? (
              employeeId ? (
                <EmployeePage
                  memberId={employeeId}
                  currentMemberId={currentId}
                  isLead={!!isLead}
                  onBack={() => setEmployeeId(null)}
                  onOpenTask={(id) => {
                    setEmployeeId(null);
                    openTaskOnBoard(id);
                  }}
                  onError={(m) => setError(m)}
                />
              ) : org ? (
                <div className="space-y-5">
                  <TeamView
                    org={org}
                    fleet={fleet}
                    currentMemberId={currentId}
                    isLead={!!isLead}
                    onOpen={setEmployeeId}
                    onChanged={async () => {
                      try {
                        setOrg(await getOrg(currentId));
                        setFleet(await getFleet(currentId));
                      } catch (e) {
                        setError(errMessage(e));
                      }
                    }}
                    onError={(m) => setError(m)}
                  />
                  <UsageCard memberId={currentId} />
                  <ReliabilityCard memberId={currentId} />
                  <EvalPanel memberId={currentId} canManage={!!isLead} />
                  <DeploymentCard memberId={currentId} />
                </div>
              ) : (
                <p className="surface p-6 text-sm text-ink/60">Loading team…</p>
              )
            ) : view === "brand" ? (
              <div className="space-y-5">
                <BrandNarrativeCard memberId={currentId} canManage={!!isLead} />
                <ChannelsPanel memberId={currentId} canManage={!!isLead} />
                <IcpMarketPanel memberId={currentId} canManage={!!isLead} />
                <OnboardingPanel
                  memberId={currentId}
                  canManage={!!isLead}
                  onChanged={onChanged}
                />
                <BrandHub
                  terms={terms}
                  atoms={atoms}
                  currentMemberId={currentId}
                  isLead={!!isLead}
                  onChanged={async () => {
                    try {
                      setTerms(await listTerms(currentId));
                    } catch (e) {
                      setError(errMessage(e));
                    }
                  }}
                  onError={(m) => setError(m)}
                />
              </div>
            ) : view === "campaigns" ? (
              campaignsPane
            ) : (
              homePane
            )}
          </div>
        </div>
      </main>
      <CommandPalette
        commands={[
          ...(["home", "campaigns", "brand", "team"] as View[]).map((v) => ({
            id: v,
            group: "Go to",
            label: VIEW_LABEL[v],
            run: () => {
              setView(v);
              setWizard(false);
            },
          })),
          {
            id: "new-idea",
            group: "Create",
            label: "New campaign from an idea",
            run: () => {
              setView("home");
              setWizard(true);
            },
          },
        ]}
      />
    </div>
  );
}

// A compact pipeline card: what it is, who owns it (human or AI), how it scores.
function KanbanCard({
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
  const assignee = members.find((m) => m.id === task.assignee_id) ?? null;
  const firstName = assignee?.display_name.split(" ")[0] ?? "";
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl border border-l-4 border-ink/10 bg-white p-3 text-left transition ${statusAccent(
        task.status,
      )} ${selected ? "ring-2 ring-forest/30" : "hover:border-ink/25"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="tlabel">{KIND_LABEL[task.kind] ?? task.kind}</span>
        <StatusBadge status={task.status} />
      </div>
      <p className="mt-1 text-sm font-medium leading-snug text-ink">{task.title}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {assignee && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-mono text-[11px] ${
              assignee.kind === "ai" ? "bg-ink/10 text-ink/60" : "bg-forest/15 text-forest"
            }`}
            title={`${assignee.display_name} (${assignee.kind === "ai" ? "AI employee" : "human"})`}
          >
            <span
              className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-semibold text-white ${
                assignee.kind === "ai" ? "bg-ink/70" : "bg-forest"
              }`}
            >
              {assignee.kind === "ai" ? "⚙" : firstName.charAt(0)}
            </span>
            {firstName}
          </span>
        )}
        <ScoreBadge score={task.score} />
      </div>
      {task.status === "needs_review" && assignee && (
        <p className="mt-1.5 font-mono text-[11px] text-amber-700">
          waiting on {firstName}
        </p>
      )}
    </button>
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
      className={`w-full rounded-2xl border-y border-r border-l-4 border-y-ink/10 border-r-ink/10 ${statusTint(
        task.status,
      )} p-4 text-left transition ${statusAccent(task.status)} ${
        selected ? "ring-2 ring-forest/30" : "hover:border-y-ink/25 hover:border-r-ink/25"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="tlabel">{KIND_LABEL[task.kind] ?? task.kind}</span>
        <StatusBadge status={task.status} />
      </div>
      <p className="mt-1.5 font-semibold text-ink">{task.title}</p>
      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        <AssigneeChip members={members} id={task.assignee_id} />
        <ScoreBadge score={task.score} />
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
