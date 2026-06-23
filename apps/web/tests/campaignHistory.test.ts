import { describe, expect, it } from "vitest";

import {
  CAMPAIGN_HISTORY_STORAGE_KEY,
  MAX_CAMPAIGN_HISTORY_RECORDS,
  createCampaignHistoryRecord,
  deleteCampaignHistoryRecord,
  loadCampaignHistory,
  upsertCampaignHistoryRecord,
  type CampaignHistoryRecord,
  type CampaignHistoryStorage,
} from "@/lib/campaignHistory";
import type {
  CampaignGenerationRequest,
  CampaignWorkflowResponse,
} from "@/lib/campaignTypes";

const request: CampaignGenerationRequest = {
  product_name: "TensorGrowth",
  product_description: "AI marketing workspace",
  target_audience: "Startup founders",
  marketing_goal: "Generate waitlist signups",
  brand_voice: "Practical",
  constraints: ["Small team"],
  user_prompt: "ready for planning",
  conversation_history: null,
  target_market: "United States",
  output_language: "English",
  selected_channels: ["LinkedIn"],
  campaign_duration: "4 weeks",
};

const response: CampaignWorkflowResponse = {
  status: "plan_generated",
  ideation_result: {
    campaign_concept: "Launch sprint",
    core_message: "Turn planning into momentum.",
    target_audience_insight: "Founders need practical output.",
    recommended_angles: ["Speed"],
    risks_or_assumptions: ["Waitlist exists"],
    follow_up_questions: [],
    is_ready_for_planning: true,
  },
  campaign_plan: {
    campaign_name: "TensorGrowth Launch Sprint",
    campaign_objective: "Generate waitlist signups",
    target_audience: "Startup founders",
    core_message: "Turn planning into momentum.",
    channels: [
      {
        channel_name: "LinkedIn",
        role_in_campaign: "Build awareness",
        content_types: ["Founder post"],
        key_messages: ["Move faster"],
        cadence: "Three posts per week",
        success_metrics: ["Clicks"],
      },
    ],
    content_pillars: ["Practical workflows"],
    timeline: [
      {
        phase_name: "Foundation",
        timing: "Week 1",
        objective: "Clarify message",
        key_activities: ["Publish narrative"],
      },
    ],
    deliverables: [
      {
        name: "Founder post",
        channel: "LinkedIn",
        format: "Text post",
        purpose: "Introduce point of view",
      },
    ],
    success_metrics: ["Signups"],
    assumptions: ["Landing page exists"],
    execution_notes: ["Keep CTA consistent"],
    draft_assets: [
      {
        asset_type: "Social post",
        channel: "LinkedIn",
        title: "Founder narrative",
        content: "Initial draft",
        call_to_action: "Join the waitlist",
        notes: ["Add proof"],
      },
    ],
  },
};

describe("campaignHistory", () => {
  it("saves and loads a campaign record", () => {
    const storage = createMemoryStorage();
    const record = createCampaignHistoryRecord({
      request,
      response,
      providerId: "mock",
      now: new Date("2026-06-23T12:00:00.000Z"),
    });

    const savedRecords = upsertCampaignHistoryRecord(record, storage);
    const loadedRecords = loadCampaignHistory(storage);

    expect(savedRecords).toHaveLength(1);
    expect(loadedRecords[0]).toMatchObject({
      title: "TensorGrowth Launch Sprint",
      provider_id: "mock",
      request: expect.objectContaining({ product_name: "TensorGrowth" }),
    });
  });

  it("keeps the newest records within the history limit", () => {
    const storage = createMemoryStorage();
    const baseRecord = createCampaignHistoryRecord({ request, response, providerId: "mock" });

    for (let index = 0; index < MAX_CAMPAIGN_HISTORY_RECORDS + 2; index += 1) {
      upsertCampaignHistoryRecord(
        {
          ...baseRecord,
          id: `record-${index}`,
          title: `Campaign ${index}`,
          created_at: new Date(Date.UTC(2026, 0, index + 1)).toISOString(),
          updated_at: new Date(Date.UTC(2026, 0, index + 1)).toISOString(),
        },
        storage,
      );
    }

    const loadedRecords = loadCampaignHistory(storage);

    expect(loadedRecords).toHaveLength(MAX_CAMPAIGN_HISTORY_RECORDS);
    expect(loadedRecords[0].id).toBe(`record-${MAX_CAMPAIGN_HISTORY_RECORDS + 1}`);
    expect(loadedRecords.some((record) => record.id === "record-0")).toBe(false);
  });

  it("deletes records by id", () => {
    const storage = createMemoryStorage();
    const firstRecord = createCampaignHistoryRecord({ request, response, providerId: "mock" });
    const secondRecord: CampaignHistoryRecord = {
      ...firstRecord,
      id: "second-record",
      title: "Second campaign",
      updated_at: "2026-06-23T12:01:00.000Z",
    };
    upsertCampaignHistoryRecord(firstRecord, storage);
    upsertCampaignHistoryRecord(secondRecord, storage);

    const remainingRecords = deleteCampaignHistoryRecord(firstRecord.id, storage);

    expect(remainingRecords).toHaveLength(1);
    expect(remainingRecords[0].id).toBe("second-record");
  });

  it("recovers safely from unreadable storage data", () => {
    const storage = createMemoryStorage({
      [CAMPAIGN_HISTORY_STORAGE_KEY]: "not-json",
    });

    expect(loadCampaignHistory(storage)).toEqual([]);
    expect(storage.getItem(CAMPAIGN_HISTORY_STORAGE_KEY)).toBeNull();
  });
});

function createMemoryStorage(
  initialItems: Record<string, string> = {},
): CampaignHistoryStorage {
  const items = new Map<string, string>(Object.entries(initialItems));
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => {
      items.set(key, value);
    },
    removeItem: (key) => {
      items.delete(key);
    },
  };
}
