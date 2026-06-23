import type { CampaignHistoryRecord } from "@/lib/campaignHistory";

interface CampaignHistoryPanelProps {
  records: CampaignHistoryRecord[];
  activeRecordId: string | null;
  onLoad: (record: CampaignHistoryRecord) => void;
  onDelete: (recordId: string) => void;
}

export function CampaignHistoryPanel({
  records,
  activeRecordId,
  onLoad,
  onDelete,
}: CampaignHistoryPanelProps) {
  return (
    <section className="panel mt-6" aria-labelledby="campaign-history-title">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Saved workspace</p>
          <h2 id="campaign-history-title" className="mt-2 text-2xl font-semibold text-ink">
            Campaign history
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Reopen recent campaign packages after refresh, then keep editing or export again.
          </p>
        </div>
        <span className="rounded-full bg-lime/40 px-3 py-1 text-xs font-semibold text-ink">
          Phase 2.2
        </span>
      </div>

      {records.length === 0 ? (
        <p className="mt-5 rounded-2xl bg-canvas p-4 text-sm leading-6 text-slate-600">
          No saved campaigns yet. Generate a package and it will be saved in this browser.
        </p>
      ) : (
        <div className="mt-5 space-y-3">
          {records.map((record) => {
            const isActive = record.id === activeRecordId;
            return (
              <article
                key={record.id}
                className={`rounded-2xl border p-4 transition ${
                  isActive
                    ? "border-moss bg-emerald-50 ring-2 ring-moss/10"
                    : "border-slate-200 bg-white"
                }`}
              >
                <button
                  type="button"
                  className="block w-full text-left"
                  onClick={() => onLoad(record)}
                  aria-pressed={isActive}
                >
                  <span className="block text-sm font-semibold text-ink">
                    {record.title}
                  </span>
                  <span className="mt-2 block text-xs leading-5 text-slate-500">
                    {buildRecordSummary(record)}
                  </span>
                  <span className="mt-2 block text-xs font-semibold text-moss">
                    Saved {formatSavedTime(record.updated_at)}
                  </span>
                </button>
                <div className="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
                  <span className="text-xs text-slate-500">
                    {record.provider_id ? `Model: ${record.provider_id}` : "Model not recorded"}
                  </span>
                  <button
                    type="button"
                    className="text-xs font-semibold text-coral hover:text-ink"
                    onClick={() => onDelete(record.id)}
                    aria-label={`Delete ${record.title}`}
                  >
                    Delete
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function buildRecordSummary(record: CampaignHistoryRecord): string {
  const market = record.request.target_market || "No market";
  const language = record.request.output_language || "No language";
  const assetCount = record.response.campaign_plan?.draft_assets?.length ?? 0;
  const assetLabel = assetCount === 1 ? "editable asset" : "editable assets";
  return `${market} / ${language} / ${assetCount} ${assetLabel}`;
}

function formatSavedTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "recently";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
