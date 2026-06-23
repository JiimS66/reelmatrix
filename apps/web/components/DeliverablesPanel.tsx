import type { CampaignDeliverable } from "@/lib/campaignTypes";

export function DeliverablesPanel({ items }: { items: CampaignDeliverable[] }) {
  return (
    <section>
      <h3 className="section-title">Deliverables</h3>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {items.map((item) => (
          <article
            key={`${item.name}-${item.channel}`}
            className="rounded-2xl border border-slate-200 bg-white p-5"
          >
            <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-wide text-moss">
              <span>{item.channel}</span>
              <span aria-hidden="true">/</span>
              <span>{item.format}</span>
            </div>
            <h4 className="mt-2 font-semibold text-ink">{item.name}</h4>
            <p className="mt-2 text-sm leading-6 text-slate-600">{item.purpose}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
