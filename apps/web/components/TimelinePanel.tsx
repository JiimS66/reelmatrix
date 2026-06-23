import type { CampaignTimelineItem } from "@/lib/campaignTypes";

export function TimelinePanel({ items }: { items: CampaignTimelineItem[] }) {
  return (
    <section>
      <h3 className="section-title">Timeline</h3>
      <div className="mt-4 space-y-4">
        {items.map((item, index) => (
          <article key={`${item.phase_name}-${item.timing}`} className="flex gap-4">
            <div className="flex flex-col items-center">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-sm font-semibold text-white">
                {index + 1}
              </span>
              {index < items.length - 1 ? (
                <span className="mt-2 h-full w-px bg-slate-200" />
              ) : null}
            </div>
            <div className="pb-5">
              <div className="flex flex-wrap items-baseline gap-3">
                <h4 className="font-semibold text-ink">{item.phase_name}</h4>
                <span className="text-xs font-medium uppercase tracking-wide text-moss">
                  {item.timing}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600">{item.objective}</p>
              <ul className="mt-3 space-y-1 text-sm text-slate-700">
                {item.key_activities.map((activity) => (
                  <li key={activity}>
                    <span aria-hidden="true">• </span>
                    {activity}
                  </li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
