"use client";

import { useEffect, useMemo, useState } from "react";

import { CampaignPlanPanel } from "@/components/CampaignPlanPanel";
import type { CampaignAsset, CampaignPlan, MarketAdaptation } from "@/lib/campaignTypes";
import { formatCampaignPackageMarkdown } from "@/lib/markdownExport";

interface CampaignPackageWorkspaceProps {
  plan: CampaignPlan;
}

type EditableAssetField = "title" | "content" | "call_to_action";

export function CampaignPackageWorkspace({ plan }: CampaignPackageWorkspaceProps) {
  const [assets, setAssets] = useState<CampaignAsset[]>(plan.draft_assets ?? []);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  useEffect(() => {
    setAssets(plan.draft_assets ?? []);
    setCopyStatus(null);
  }, [plan]);

  const planWithEdits = useMemo<CampaignPlan>(
    () => ({ ...plan, draft_assets: assets }),
    [assets, plan],
  );
  const markdown = useMemo(
    () => formatCampaignPackageMarkdown(planWithEdits),
    [planWithEdits],
  );

  function updateAsset(index: number, field: EditableAssetField, value: string) {
    setAssets((current) =>
      current.map((asset, assetIndex) =>
        assetIndex === index ? { ...asset, [field]: value } : asset,
      ),
    );
  }

  async function copyMarkdown() {
    if (!navigator.clipboard) {
      setCopyStatus("Clipboard is not available in this browser.");
      return;
    }
    await navigator.clipboard.writeText(markdown);
    setCopyStatus("Campaign package copied as Markdown.");
  }

  function exportMarkdown() {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${slugify(plan.campaign_name)}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <section className="panel flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Campaign package</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">
            Edit, copy, and export the first draft
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Treat this as a lightweight workspace: refine the generated assets, copy
            the full package, or export Markdown for Notion, Docs, Feishu, or a client brief.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="button-secondary" type="button" onClick={copyMarkdown}>
            Copy Markdown
          </button>
          <button className="button-primary" type="button" onClick={exportMarkdown}>
            Export Markdown
          </button>
        </div>
        {copyStatus ? (
          <p role="status" className="basis-full text-sm font-semibold text-moss">
            {copyStatus}
          </p>
        ) : null}
      </section>

      <CampaignPlanPanel plan={planWithEdits} />

      {plan.market_adaptation ? (
        <MarketAdaptationPanel adaptation={plan.market_adaptation} />
      ) : null}

      <EditableAssetsPanel assets={assets} onUpdate={updateAsset} />
    </div>
  );
}

function MarketAdaptationPanel({ adaptation }: { adaptation: MarketAdaptation }) {
  return (
    <section className="panel space-y-6" aria-labelledby="market-adaptation-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Cross-border fit</p>
          <h2 id="market-adaptation-title" className="mt-2 text-2xl font-semibold text-ink">
            Market adaptation for {adaptation.target_market}
          </h2>
        </div>
        <span className="rounded-full bg-lime/40 px-3 py-1 text-xs font-semibold text-ink">
          Localization notes
        </span>
      </div>
      <div className="rounded-2xl bg-ink p-5 text-sm leading-6 text-white/80">
        {adaptation.language_strategy}
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <ListBlock title="Positioning" items={adaptation.positioning_recommendations} />
        <ListBlock title="Localization" items={adaptation.localization_notes} />
        <ListBlock title="Risks" items={adaptation.cultural_risks} />
        <ListBlock title="Suggested phrases" items={adaptation.suggested_phrases} />
      </div>
    </section>
  );
}

function EditableAssetsPanel({
  assets,
  onUpdate,
}: {
  assets: CampaignAsset[];
  onUpdate: (index: number, field: EditableAssetField, value: string) => void;
}) {
  return (
    <section className="panel space-y-5" aria-labelledby="draft-assets-title">
      <div>
        <p className="eyebrow">First-draft materials</p>
        <h2 id="draft-assets-title" className="mt-2 text-2xl font-semibold text-ink">
          Editable channel assets
        </h2>
      </div>

      {assets.length === 0 ? (
        <p className="rounded-2xl bg-canvas p-5 text-sm text-slate-600">
          This provider did not return editable draft assets. Regenerate with mock or ask
          the model to include channel-specific materials.
        </p>
      ) : (
        <div className="space-y-4">
          {assets.map((asset, index) => (
            <article key={`${asset.channel}-${index}`} className="rounded-3xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-moss">
                    {asset.channel} / {asset.asset_type}
                  </p>
                  <label className="sr-only" htmlFor={`asset-title-${index}`}>
                    Asset title
                  </label>
                  <input
                    id={`asset-title-${index}`}
                    className="mt-2 w-full rounded-xl border border-transparent bg-canvas px-3 py-2 text-lg font-semibold text-ink outline-none focus:border-moss focus:ring-4 focus:ring-moss/10"
                    value={asset.title}
                    onChange={(event) => onUpdate(index, "title", event.target.value)}
                  />
                </div>
              </div>
              <label className="label mt-4" htmlFor={`asset-content-${index}`}>
                Draft copy
              </label>
              <textarea
                id={`asset-content-${index}`}
                className="input mt-2 min-h-44 resize-y"
                value={asset.content}
                onChange={(event) => onUpdate(index, "content", event.target.value)}
              />
              <label className="label mt-4" htmlFor={`asset-cta-${index}`}>
                Call to action
              </label>
              <input
                id={`asset-cta-${index}`}
                className="input mt-2"
                value={asset.call_to_action}
                onChange={(event) => onUpdate(index, "call_to_action", event.target.value)}
              />
              {asset.notes.length > 0 ? (
                <div className="mt-4 rounded-2xl bg-canvas p-4">
                  <h3 className="section-title">Editing notes</h3>
                  <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-600">
                    {asset.notes.map((note) => (
                      <li key={note}>- {note}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/70 p-5">
      <h3 className="section-title">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
        {items.map((item) => (
          <li key={item} className="flex gap-3">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-moss" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "") || "campaign-package";
}
