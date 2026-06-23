import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CampaignHistoryPanel } from "@/components/CampaignHistoryPanel";
import type { CampaignHistoryRecord } from "@/lib/campaignHistory";

const record: CampaignHistoryRecord = {
  id: "history-record-1",
  title: "TensorGrowth Launch Sprint",
  created_at: "2026-06-23T12:00:00.000Z",
  updated_at: "2026-06-23T12:00:00.000Z",
  provider_id: "mock",
  request: {
    product_name: "TensorGrowth",
    product_description: "AI marketing workspace",
    target_audience: "Startup founders",
    marketing_goal: "Generate signups",
    brand_voice: "Practical",
    constraints: null,
    user_prompt: "ready for planning",
    conversation_history: null,
    target_market: "United States",
    output_language: "English",
    selected_channels: ["LinkedIn"],
    campaign_duration: "4 weeks",
  },
  response: {
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
      campaign_objective: "Generate signups",
      target_audience: "Startup founders",
      core_message: "Turn planning into momentum.",
      channels: [],
      content_pillars: [],
      timeline: [],
      deliverables: [],
      success_metrics: ["Signups"],
      assumptions: [],
      execution_notes: [],
      draft_assets: [
        {
          asset_type: "Social post",
          channel: "LinkedIn",
          title: "Founder narrative",
          content: "Initial draft",
          call_to_action: "Join the waitlist",
          notes: [],
        },
      ],
    },
  },
};

describe("CampaignHistoryPanel", () => {
  it("renders an empty state", () => {
    render(
      <CampaignHistoryPanel
        records={[]}
        activeRecordId={null}
        onLoad={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText(/No saved campaigns yet/)).toBeInTheDocument();
  });

  it("loads and deletes saved campaign records", async () => {
    const user = userEvent.setup();
    const onLoad = vi.fn();
    const onDelete = vi.fn();

    render(
      <CampaignHistoryPanel
        records={[record]}
        activeRecordId="history-record-1"
        onLoad={onLoad}
        onDelete={onDelete}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: /United States \/ English \/ 1 editable asset/,
      }),
    );
    await user.click(screen.getByRole("button", { name: "Delete TensorGrowth Launch Sprint" }));

    expect(onLoad).toHaveBeenCalledWith(record);
    expect(onDelete).toHaveBeenCalledWith("history-record-1");
    expect(screen.getByText(/United States \/ English \/ 1 editable asset/)).toBeInTheDocument();
  });
});
