import { ChannelPlanCard } from "@/components/ChannelPlanCard";
import { DeliverablesPanel } from "@/components/DeliverablesPanel";
import { TimelinePanel } from "@/components/TimelinePanel";
import type { CampaignPlan } from "@/lib/campaignTypes";

export function CampaignPlanPanel({ plan }: { plan: CampaignPlan }) {
  return (
    <section className="panel space-y-8" aria-labelledby="campaign-plan-title">
      <div className="rounded-3xl bg-moss p-6 text-white sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lime">
          Integrated campaign plan
        </p>
        <h2 id="campaign-plan-title" className="mt-3 text-3xl font-semibold">
          {plan.campaign_name}
        </h2>
        <dl className="mt-6 grid gap-5 text-sm sm:grid-cols-2">
          <SummaryItem label="Objective" value={plan.campaign_objective} />
          <SummaryItem label="Target audience" value={plan.target_audience} />
          <div className="sm:col-span-2">
            <SummaryItem label="Core message" value={plan.core_message} />
          </div>
        </dl>
      </div>

      <section>
        <h3 className="section-title">Channel plan</h3>
        <div className="mt-4 space-y-4">
          {plan.channels.map((channel) => (
            <ChannelPlanCard key={channel.channel_name} channel={channel} />
          ))}
        </div>
      </section>

      <ListSection title="Content pillars" items={plan.content_pillars} />

      <div className="grid gap-8 lg:grid-cols-2">
        <TimelinePanel items={plan.timeline} />
        <DeliverablesPanel items={plan.deliverables} />
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <ListSection title="Success metrics" items={plan.success_metrics} compact />
        <ListSection title="Assumptions" items={plan.assumptions} compact />
        <ListSection title="Execution notes" items={plan.execution_notes} compact />
      </div>
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-lime">
        {label}
      </dt>
      <dd className="mt-2 leading-6 text-white/85">{value}</dd>
    </div>
  );
}

function ListSection({
  title,
  items,
  compact = false,
}: {
  title: string;
  items: string[];
  compact?: boolean;
}) {
  return (
    <section className={compact ? "rounded-2xl bg-canvas p-5" : undefined}>
      <h3 className="section-title">{title}</h3>
      <ul
        className={`mt-3 ${
          compact ? "space-y-2" : "grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
        }`}
      >
        {items.map((item) => (
          <li
            key={item}
            className={
              compact
                ? "text-sm leading-6 text-slate-600"
                : "rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
            }
          >
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
