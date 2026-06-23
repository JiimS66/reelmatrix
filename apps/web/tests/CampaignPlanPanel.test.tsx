import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CampaignPlanPanel } from "@/components/CampaignPlanPanel";
import type { CampaignPlan } from "@/lib/campaignTypes";

const plan: CampaignPlan = {
  campaign_name: "TensorGrowth Lean Growth Launch",
  campaign_objective: "Generate qualified waitlist signups",
  target_audience: "Early-stage startup founders",
  core_message: "Turn a clear product story into measurable momentum.",
  channels: [
    {
      channel_name: "LinkedIn",
      role_in_campaign: "Build category awareness",
      content_types: ["Founder posts"],
      key_messages: ["Make campaign planning practical"],
      cadence: "Three posts per week",
      success_metrics: ["Waitlist conversions"],
    },
  ],
  content_pillars: ["Practical AI workflows"],
  timeline: [
    {
      phase_name: "Foundation",
      timing: "Week 1",
      objective: "Establish the campaign promise",
      key_activities: ["Publish the category narrative"],
    },
  ],
  deliverables: [
    {
      name: "Founder launch narrative",
      channel: "LinkedIn",
      format: "Text post",
      purpose: "Introduce the campaign point of view",
    },
  ],
  success_metrics: ["Qualified waitlist signups"],
  assumptions: ["A waitlist destination exists"],
  execution_notes: ["Keep calls to action consistent"],
};

describe("CampaignPlanPanel", () => {
  it("renders channels, timeline, and deliverables structurally", () => {
    render(<CampaignPlanPanel plan={plan} />);

    expect(screen.getByRole("heading", { name: "LinkedIn" })).toBeInTheDocument();
    expect(screen.getByText("Foundation")).toBeInTheDocument();
    expect(screen.getByText("Publish the category narrative")).toBeInTheDocument();
    expect(screen.getByText("Founder launch narrative")).toBeInTheDocument();
    expect(screen.getByText("Text post")).toBeInTheDocument();
  });
});
