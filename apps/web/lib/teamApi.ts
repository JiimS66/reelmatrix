const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type MemberKind = "human" | "ai";
export type MemberRole = "lead" | "member";
export type TaskKind =
  | "ideation"
  | "planning"
  | "asset"
  | "visual"
  | "claim_check";
export type TaskStatus =
  | "todo"
  | "in_progress"
  | "needs_review"
  | "done"
  | "blocked";
export type ExecutionMode = "ai_draft_human_review" | "ai_auto" | "human_only";

export interface Member {
  id: string;
  kind: MemberKind;
  role: MemberRole;
  display_name: string;
}

export interface CheckIssue {
  code: string;
  detail: string;
}

export interface Task {
  id: string;
  campaign_id: string;
  kind: TaskKind;
  title: string;
  status: TaskStatus;
  execution_mode: ExecutionMode;
  assignee_id: string | null;
  depends_on: string[];
  sequence: number;
  params: Record<string, unknown>;
  output: Record<string, unknown> | null;
  checks: Record<string, CheckIssue[]>;
  score: { overall: number; dimensions: Record<string, number> } | null;
  due_date: string | null;
  phase: string | null;
  updated_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  template: string;
  status: string;
  event_name: string | null;
  event_date: string | null;
}

export interface Milestone {
  id: string;
  phase: string;
  name: string;
  date: string;
  offset_days: number;
  objective: string;
}

export interface ScheduleData {
  campaign: Campaign;
  milestones: Milestone[];
  tasks: Task[];
  timely_angles: string[];
}

export interface TodoItem {
  campaign_name: string;
  task: Task;
}

export interface Board {
  campaign: Campaign;
  tasks: Task[];
  members: Member[];
}

export interface Comment {
  id: string;
  author_id: string;
  body: string;
  created_at: string;
}

export interface TaskEvent {
  id: string;
  type: string;
  actor_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface TaskDetail {
  task: Task;
  ai_draft: Record<string, unknown> | null;
  comments: Comment[];
  events: TaskEvent[];
  available_actions: string[];
}

export interface Atom {
  id: string;
  kind: string;
  text: string;
  tags: string[];
  source_campaign_id: string | null;
  created_at: string;
}

export interface PostPerformance {
  post_id: string;
  title: string;
  url: string;
  published_at: string;
  publish_status: string;
  permalink: string | null;
  impressions: number;
  clicks: number;
  signups: number;
  source: string;
}

export interface PlatformPerformance {
  platform: string;
  impressions: number;
  clicks: number;
  signups: number;
  posts: PostPerformance[];
}

export interface PerformanceData {
  campaign_id: string;
  platforms: PlatformPerformance[];
  totals: Record<string, number>;
  note: string;
}

export interface OrgMember {
  id: string;
  kind: MemberKind;
  role: MemberRole;
  display_name: string;
  job_description: string;
  reports_to: string | null;
  handles_kinds: string[];
  agent_role: string | null;
  provider: string | null;
  model: string | null;
}

export interface AgentRoleInfo {
  key: string;
  title: string;
  job_description: string;
}

export interface OrgData {
  members: OrgMember[];
  task_kinds: string[];
  agent_roles: AgentRoleInfo[];
}

export class TeamApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "TeamApiError";
  }
}

async function request<T>(
  path: string,
  opts: { method?: string; memberId?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.memberId) headers["X-Member-Id"] = opts.memberId;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new TeamApiError("Cannot reach the backend API on :8000. Is it running?");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // keep the default
    }
    throw new TeamApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const listMembers = () => request<Member[]>("/api/v1/team/members");

export const listCampaigns = (memberId: string) =>
  request<Campaign[]>("/api/v1/team/campaigns", { memberId });

export const createCampaign = (
  memberId: string,
  body: {
    name: string;
    brief: Record<string, unknown>;
    template?: string;
    event_name?: string;
    event_date?: string;
    review_assets?: boolean;
    with_visuals?: boolean;
  },
) => request<Board>("/api/v1/team/campaigns", { method: "POST", memberId, body });

export const getSchedule = (memberId: string, campaignId: string) =>
  request<ScheduleData>(`/api/v1/team/campaigns/${campaignId}/schedule`, {
    memberId,
  });

export const refreshTrends = (memberId: string, campaignId: string) =>
  request<{ campaign_id: string; timely_angles: string[] }>(
    `/api/v1/team/campaigns/${campaignId}/trends`,
    { method: "POST", memberId },
  );

export const getTodo = (memberId: string) =>
  request<TodoItem[]>("/api/v1/team/todo", { memberId });

export const getPerformance = (memberId: string, campaignId: string) =>
  request<PerformanceData>(
    `/api/v1/team/campaigns/${campaignId}/performance`,
    { memberId },
  );

export interface FleetAgent {
  member_id: string;
  display_name: string;
  role: string;
  provider: string;
  model: string | null;
  runs: number;
  tasks_owned: number;
  avg_score: number | null;
  self_corrections: number;
}

export const getFleet = (memberId: string) =>
  request<FleetAgent[]>("/api/v1/team/fleet", { memberId });

export const syncAnalytics = (memberId: string, campaignId: string) =>
  request<PerformanceData>(
    `/api/v1/team/campaigns/${campaignId}/analytics/sync`,
    { method: "POST", memberId },
  );

export const publishCampaign = (memberId: string, campaignId: string) =>
  request<PerformanceData>(`/api/v1/team/campaigns/${campaignId}/publish`, {
    method: "POST",
    memberId,
  });

export const recordMetrics = (
  memberId: string,
  postId: string,
  body: { impressions: number; clicks: number; signups: number },
) =>
  request<PerformanceData>(`/api/v1/team/posts/${postId}/metrics`, {
    method: "POST",
    memberId,
    body,
  });

export const getBoard = (memberId: string, campaignId: string) =>
  request<Board>(`/api/v1/team/campaigns/${campaignId}/board`, { memberId });

export const runCampaign = (memberId: string, campaignId: string) =>
  request<Board>(`/api/v1/team/campaigns/${campaignId}/run`, {
    method: "POST",
    memberId,
  });

export const getInbox = (memberId: string) =>
  request<Task[]>("/api/v1/team/inbox", { memberId });

export const getTask = (memberId: string, taskId: string) =>
  request<TaskDetail>(`/api/v1/team/tasks/${taskId}`, { memberId });

export const editTask = (
  memberId: string,
  taskId: string,
  output: Record<string, unknown>,
) =>
  request<Task>(`/api/v1/team/tasks/${taskId}/edit`, {
    method: "POST",
    memberId,
    body: { output },
  });

export const reviewTask = (
  memberId: string,
  taskId: string,
  body: {
    action: "approve" | "request_changes";
    output?: Record<string, unknown> | null;
    note?: string | null;
  },
) =>
  request<Board>(`/api/v1/team/tasks/${taskId}/review`, {
    method: "POST",
    memberId,
    body,
  });

export const assignTask = (
  memberId: string,
  taskId: string,
  body: { member_id?: string | null; execution_mode?: ExecutionMode | null },
) =>
  request<Task>(`/api/v1/team/tasks/${taskId}/assign`, {
    method: "POST",
    memberId,
    body,
  });

export const submitTask = (
  memberId: string,
  taskId: string,
  output?: Record<string, unknown> | null,
) =>
  request<Task>(`/api/v1/team/tasks/${taskId}/submit`, {
    method: "POST",
    memberId,
    body: { output: output ?? null },
  });

export const addComment = (memberId: string, taskId: string, bodyText: string) =>
  request<Comment>(`/api/v1/team/tasks/${taskId}/comments`, {
    method: "POST",
    memberId,
    body: { body: bodyText },
  });

export interface BrandTermItem {
  id: string;
  term: string;
  term_type: string;
  replacement: string | null;
  case_sensitive: boolean;
  note: string;
}

export const listTerms = (memberId: string) =>
  request<BrandTermItem[]>("/api/v1/team/terms", { memberId });

export const createTerm = (
  memberId: string,
  body: {
    term: string;
    term_type: string;
    replacement?: string | null;
    case_sensitive?: boolean;
    note?: string;
  },
) => request<BrandTermItem[]>("/api/v1/team/terms", { method: "POST", memberId, body });

export const deleteTerm = (memberId: string, termId: string) =>
  request<BrandTermItem[]>(`/api/v1/team/terms/${termId}`, {
    method: "DELETE",
    memberId,
  });

export const listAtoms = (
  memberId: string,
  params?: { kind?: string; tag?: string },
) => {
  const query = new URLSearchParams();
  if (params?.kind) query.set("kind", params.kind);
  if (params?.tag) query.set("tag", params.tag);
  const qs = query.toString();
  return request<Atom[]>(`/api/v1/team/atoms${qs ? `?${qs}` : ""}`, { memberId });
};

export const getOrg = (memberId: string) =>
  request<OrgData>("/api/v1/team/org", { memberId });

export const createOrgMember = (
  memberId: string,
  body: {
    display_name: string;
    role: string;
    job_description?: string;
    handles_kinds?: string[];
    provider?: string;
    model?: string | null;
    reports_to?: string | null;
  },
) =>
  request<OrgMember>("/api/v1/team/org/members", {
    method: "POST",
    memberId,
    body,
  });

export const updateOrgMember = (
  memberId: string,
  targetId: string,
  body: {
    job_description?: string;
    handles_kinds?: string[];
    reports_to?: string | null;
    role?: string;
    provider?: string;
    model?: string | null;
  },
) =>
  request<OrgMember>(`/api/v1/team/org/members/${targetId}`, {
    method: "POST",
    memberId,
    body,
  });

export const TESTSPRITE_BRIEF: Record<string, unknown> = {
  product_name: "TestSprite",
  product_description:
    "An agentic testing platform that verifies AI-generated code with live browsers and APIs.",
  target_audience: "Engineering leaders and AI-native developers using coding agents",
  marketing_goal: "Generate qualified developer signups and API key starts",
  user_prompt: "ready for planning: launch campaign for TestSprite",
  selected_channels: ["LinkedIn", "Email", "Landing Page"],
};
