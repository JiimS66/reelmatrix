import { describe, expect, it } from "vitest";

import type { CampaignPlan } from "@/lib/campaignTypes";
import { formatCampaignPackageMarkdown } from "@/lib/markdownExport";

const plan: CampaignPlan = {
  campaign_name: "TensorGrowth Cross-Border Launch Sprint",
  campaign_objective: "Generate qualified waitlist signups",
  target_audience: "Early-stage startup founders",
  core_message: "Turn planning into measurable momentum.",
  channels: [
    {
      channel_name: "Email",
      role_in_campaign: "Convert demand",
      content_types: ["Launch sequence"],
      key_messages: ["Move from idea to campaign assets"],
      cadence: "One email per week",
      success_metrics: ["Click-through rate"],
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
      name: "Waitlist sequence",
      channel: "Email",
      format: "Three emails",
      purpose: "Convert interested prospects",
    },
  ],
  success_metrics: ["Qualified signups"],
  assumptions: ["A waitlist destination exists"],
  execution_notes: ["Keep calls to action consistent"],
  claim_checks: [
    {
      claim: "TestSprite announced $6.7M in seed funding",
      status: "source_backed",
      source: "https://www.geekwire.com/",
    },
    {
      claim: "Any added customer claim must be validated before publishing.",
      status: "needs_validation",
      source: null,
    },
  ],
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
      asset_type: "Email sequence",
      channel: "Email",
      title: "Waitlist conversion sequence",
      content: "Email 1: Name the bottleneck.",
      call_to_action: "Generate a campaign package.",
      notes: ["Keep it concise"],
    },
  ],
};

describe("formatCampaignPackageMarkdown", () => {
  it("includes plan, claim checks, market adaptation, and draft assets", () => {
    const markdown = formatCampaignPackageMarkdown(plan);

    expect(markdown).toContain("# TensorGrowth Cross-Border Launch Sprint");
    expect(markdown).toContain("## Claim Checks");
    expect(markdown).toContain("[source-backed] TestSprite announced $6.7M in seed funding");
    expect(markdown).toContain("[needs validation] Any added customer claim");
    expect(markdown).toContain("## Market Adaptation");
    expect(markdown).toContain("**Target market:** United States");
    expect(markdown).toContain("## Draft Assets");
    expect(markdown).toContain("Email 1: Name the bottleneck.");
  });
});
