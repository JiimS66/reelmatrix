import type { CampaignChannelPlan } from "@/lib/campaignTypes";

export function ChannelPlanCard({ channel }: { channel: CampaignChannelPlan }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-moss">
            Channel
          </p>
          <h4 className="mt-1 text-xl font-semibold text-ink">{channel.channel_name}</h4>
        </div>
        <span className="rounded-full bg-canvas px-3 py-1 text-xs font-medium text-slate-600">
          {channel.cadence}
        </span>
      </div>
      <p className="mt-4 text-sm leading-6 text-slate-600">{channel.role_in_campaign}</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <MiniList title="Content" items={channel.content_types} />
        <MiniList title="Messages" items={channel.key_messages} />
        <MiniList title="Metrics" items={channel.success_metrics} />
      </div>
    </article>
  );
}

function MiniList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h5>
      <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
