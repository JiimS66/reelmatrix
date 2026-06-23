import type { IdeationResult } from "@/lib/campaignTypes";

interface IdeationResultPanelProps {
  result: IdeationResult;
}

export function IdeationResultPanel({ result }: IdeationResultPanelProps) {
  return (
    <section className="panel space-y-6" aria-labelledby="ideation-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Strategy signal</p>
          <h2 id="ideation-title" className="mt-2 text-2xl font-semibold text-ink">
            Ideation result
          </h2>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            result.is_ready_for_planning
              ? "bg-emerald-100 text-emerald-800"
              : "bg-amber-100 text-amber-800"
          }`}
        >
          {result.is_ready_for_planning ? "Ready for planning" : "Needs clarification"}
        </span>
      </div>

      <div className="rounded-2xl bg-ink p-5 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lime">
          Campaign concept
        </p>
        <p className="mt-3 text-xl font-semibold">{result.campaign_concept}</p>
        <p className="mt-3 text-sm leading-6 text-white/75">{result.core_message}</p>
      </div>

      <div>
        <h3 className="section-title">Audience insight</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {result.target_audience_insight}
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <ListBlock title="Recommended angles" items={result.recommended_angles} />
        <ListBlock title="Risks & assumptions" items={result.risks_or_assumptions} />
      </div>

      {result.follow_up_questions.length > 0 ? (
        <ListBlock title="Follow-up questions" items={result.follow_up_questions} />
      ) : null}
    </section>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/70 p-5">
      <h3 className="section-title">{title}</h3>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
          {items.map((item) => (
            <li key={item} className="flex gap-3">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-moss" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">None identified.</p>
      )}
    </div>
  );
}
