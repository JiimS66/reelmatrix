import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CampaignPackageWorkspace } from "@/components/CampaignPackageWorkspace";
import type { CampaignPlan } from "@/lib/campaignTypes";

const plan: CampaignPlan = {
  campaign_name: "TensorGrowth Cross-Border Launch Sprint",
  campaign_objective: "Generate qualified waitlist signups",
  target_audience: "Early-stage startup founders",
  core_message: "Turn planning into measurable momentum.",
  channels: [
    {
      channel_name: "LinkedIn",
      role_in_campaign: "Build credibility",
      content_types: ["Founder post"],
      key_messages: ["Move from idea to campaign assets"],
      cadence: "Three posts per week",
      success_metrics: ["Waitlist clicks"],
    },
  ],
  content_pillars: ["Practical AI workflows"],
  timeline: [
    {
      phase_name: "Foundation",
      timing: "Week 1",
      objective: "Clarify the promise",
      key_activities: ["Publish the category narrative"],
    },
  ],
  deliverables: [
    {
      name: "Founder narrative",
      channel: "LinkedIn",
      format: "Text post",
      purpose: "Introduce the point of view",
    },
  ],
  success_metrics: ["Qualified waitlist signups"],
  assumptions: ["A waitlist destination exists"],
  execution_notes: ["Keep calls to action consistent"],
  market_adaptation: {
    target_market: "United States",
    language_strategy: "Use concise English copy.",
    positioning_recommendations: ["Lead with practical outcomes"],
    localization_notes: ["Avoid literal translation"],
    cultural_risks: ["Do not overpromise automation"],
    suggested_phrases: ["Build a campaign package in one session"],
  },
  draft_assets: [
    {
      asset_type: "Social post",
      channel: "LinkedIn",
      title: "Founder launch narrative",
      content: "Initial LinkedIn draft.",
      call_to_action: "Join the waitlist.",
      notes: ["Add proof before publishing"],
    },
  ],
};

describe("CampaignPackageWorkspace", () => {
  it("renders market adaptation and editable draft assets", async () => {
    const user = userEvent.setup();
    render(<CampaignPackageWorkspace plan={plan} />);

    expect(screen.getByRole("heading", { name: /Market adaptation for United States/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Markdown" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export Markdown" })).toBeInTheDocument();

    const draftCopy = screen.getByLabelText("Draft copy");
    await user.clear(draftCopy);
    await user.type(draftCopy, "Edited LinkedIn draft.");

    expect(draftCopy).toHaveValue("Edited LinkedIn draft.");
  });
});
