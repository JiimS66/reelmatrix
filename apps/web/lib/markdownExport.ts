import type { CampaignPlan } from "@/lib/campaignTypes";

export function formatCampaignPackageMarkdown(plan: CampaignPlan): string {
  const lines = [
    `# ${plan.campaign_name}`,
    "",
    `**Objective:** ${plan.campaign_objective}`,
    `**Target audience:** ${plan.target_audience}`,
    `**Core message:** ${plan.core_message}`,
    "",
    "## Channel Plan",
    ...plan.channels.flatMap((channel) => [
      "",
      `### ${channel.channel_name}`,
      `- Role: ${channel.role_in_campaign}`,
      `- Cadence: ${channel.cadence}`,
      `- Content types: ${channel.content_types.join(", ")}`,
      `- Key messages: ${channel.key_messages.join("; ")}`,
      `- Success metrics: ${channel.success_metrics.join(", ")}`,
    ]),
    "",
    "## Content Pillars",
    ...asBullets(plan.content_pillars),
    "",
    "## Timeline",
    ...plan.timeline.flatMap((item) => [
      "",
      `### ${item.phase_name} (${item.timing})`,
      `- Objective: ${item.objective}`,
      `- Activities: ${item.key_activities.join("; ")}`,
    ]),
    "",
    "## Deliverables",
    ...plan.deliverables.map(
      (item) => `- ${item.name} (${item.channel}, ${item.format}): ${item.purpose}`,
    ),
    "",
    "## Success Metrics",
    ...asBullets(plan.success_metrics),
    "",
    "## Execution Notes",
    ...asBullets(plan.execution_notes),
  ];

  if (plan.market_adaptation) {
    lines.push(
      "",
      "## Market Adaptation",
      `**Target market:** ${plan.market_adaptation.target_market}`,
      `**Language strategy:** ${plan.market_adaptation.language_strategy}`,
      "",
      "### Positioning Recommendations",
      ...asBullets(plan.market_adaptation.positioning_recommendations),
      "",
      "### Localization Notes",
      ...asBullets(plan.market_adaptation.localization_notes),
      "",
      "### Cultural Risks",
      ...asBullets(plan.market_adaptation.cultural_risks),
      "",
      "### Suggested Phrases",
      ...asBullets(plan.market_adaptation.suggested_phrases),
    );
  }

  if (plan.draft_assets?.length) {
    lines.push(
      "",
      "## Draft Assets",
      ...plan.draft_assets.flatMap((asset) => [
        "",
        `### ${asset.title}`,
        `- Type: ${asset.asset_type}`,
        `- Channel: ${asset.channel}`,
        "",
        asset.content,
        "",
        `**CTA:** ${asset.call_to_action}`,
        "",
        "Notes:",
        ...asBullets(asset.notes),
      ]),
    );
  }

  return `${lines.join("\n").replace(/\n{3,}/g, "\n\n")}\n`;
}

function asBullets(items: string[]): string[] {
  if (items.length === 0) {
    return ["- None"];
  }
  return items.map((item) => `- ${item}`);
}
