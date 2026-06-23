import type {
  CampaignGenerationRequest,
  CampaignWorkflowResponse,
} from "@/lib/campaignTypes";

export const CAMPAIGN_HISTORY_STORAGE_KEY = "reelmatrix.campaignHistory.v1";
export const MAX_CAMPAIGN_HISTORY_RECORDS = 10;

export interface CampaignHistoryRecord {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  provider_id: string | null;
  request: CampaignGenerationRequest;
  response: CampaignWorkflowResponse;
}

export interface CampaignHistoryStorage {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
}

interface CreateCampaignHistoryRecordInput {
  request: CampaignGenerationRequest;
  response: CampaignWorkflowResponse;
  providerId?: string | null;
  now?: Date;
}

export function createCampaignHistoryRecord({
  request,
  response,
  providerId = null,
  now = new Date(),
}: CreateCampaignHistoryRecordInput): CampaignHistoryRecord {
  const timestamp = now.toISOString();
  const title =
    response.campaign_plan?.campaign_name?.trim() ||
    request.product_name.trim() ||
    "Untitled campaign";

  return {
    id: `campaign-${now.getTime()}-${Math.random().toString(36).slice(2, 8)}`,
    title,
    created_at: timestamp,
    updated_at: timestamp,
    provider_id: providerId,
    request,
    response,
  };
}

export function loadCampaignHistory(
  storage: CampaignHistoryStorage | null = getBrowserStorage(),
): CampaignHistoryRecord[] {
  if (!storage) {
    return [];
  }

  const rawHistory = storage.getItem(CAMPAIGN_HISTORY_STORAGE_KEY);
  if (!rawHistory) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawHistory) as unknown;
    if (!Array.isArray(parsed)) {
      storage.removeItem(CAMPAIGN_HISTORY_STORAGE_KEY);
      return [];
    }

    return normalizeCampaignHistory(parsed.filter(isCampaignHistoryRecord));
  } catch {
    storage.removeItem(CAMPAIGN_HISTORY_STORAGE_KEY);
    return [];
  }
}

export function saveCampaignHistory(
  records: CampaignHistoryRecord[],
  storage: CampaignHistoryStorage | null = getBrowserStorage(),
): CampaignHistoryRecord[] {
  const normalizedRecords = normalizeCampaignHistory(records);
  if (storage) {
    storage.setItem(
      CAMPAIGN_HISTORY_STORAGE_KEY,
      JSON.stringify(normalizedRecords),
    );
  }
  return normalizedRecords;
}

export function upsertCampaignHistoryRecord(
  record: CampaignHistoryRecord,
  storage: CampaignHistoryStorage | null = getBrowserStorage(),
): CampaignHistoryRecord[] {
  const existingRecords = loadCampaignHistory(storage);
  return saveCampaignHistory(
    [record, ...existingRecords.filter((item) => item.id !== record.id)],
    storage,
  );
}

export function deleteCampaignHistoryRecord(
  recordId: string,
  storage: CampaignHistoryStorage | null = getBrowserStorage(),
): CampaignHistoryRecord[] {
  const nextRecords = loadCampaignHistory(storage).filter(
    (record) => record.id !== recordId,
  );
  return saveCampaignHistory(nextRecords, storage);
}

export function clearCampaignHistory(
  storage: CampaignHistoryStorage | null = getBrowserStorage(),
): void {
  storage?.removeItem(CAMPAIGN_HISTORY_STORAGE_KEY);
}

function getBrowserStorage(): CampaignHistoryStorage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function normalizeCampaignHistory(
  records: CampaignHistoryRecord[],
): CampaignHistoryRecord[] {
  return [...records]
    .sort((first, second) => Date.parse(second.updated_at) - Date.parse(first.updated_at))
    .slice(0, MAX_CAMPAIGN_HISTORY_RECORDS);
}

function isCampaignHistoryRecord(value: unknown): value is CampaignHistoryRecord {
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string" &&
    isValidDate(value.created_at) &&
    isValidDate(value.updated_at) &&
    (typeof value.provider_id === "string" || value.provider_id === null) &&
    isObject(value.request) &&
    isCampaignWorkflowResponse(value.response)
  );
}

function isCampaignWorkflowResponse(value: unknown): value is CampaignWorkflowResponse {
  if (!isObject(value)) {
    return false;
  }

  return (
    (value.status === "needs_more_ideation" || value.status === "plan_generated") &&
    isObject(value.ideation_result) &&
    "campaign_plan" in value
  );
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isValidDate(value: string): boolean {
  return !Number.isNaN(Date.parse(value));
}
