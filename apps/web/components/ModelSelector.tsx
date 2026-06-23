import type {
  LLMProviderInfo,
  LLMProviderKind,
} from "@/lib/campaignTypes";

interface ModelSelectorProps {
  providers: LLMProviderInfo[];
  selectedProviderId: string;
  onChange: (providerId: string) => void;
  isLoading: boolean;
  error: string | null;
}

const providerGroups: Array<{
  kind: LLMProviderKind;
  title: string;
  subtitle: string;
}> = [
  {
    kind: "local",
    title: "Local model",
    subtitle: "OpenAI-compatible service running in your environment.",
  },
  {
    kind: "remote",
    title: "Remote models",
    subtitle: "Hosted providers configured by the backend.",
  },
  {
    kind: "development",
    title: "Development",
    subtitle: "Deterministic mode for tests and local demos.",
  },
];

export function ModelSelector({
  providers,
  selectedProviderId,
  onChange,
  isLoading,
  error,
}: ModelSelectorProps) {
  return (
    <section className="panel mb-6" aria-labelledby="model-provider-title">
      <p className="eyebrow">Model routing</p>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="model-provider-title" className="text-2xl font-semibold text-ink">
            Choose a model provider
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Each campaign request uses the selected provider without changing backend
            global configuration.
          </p>
        </div>
        {selectedProviderId ? (
          <span className="rounded-full bg-lime/40 px-3 py-1 text-xs font-semibold text-ink">
            Request-level
          </span>
        ) : null}
      </div>

      {isLoading ? (
        <p role="status" className="mt-5 text-sm text-slate-500">
          Loading configured models…
        </p>
      ) : null}

      {error ? (
        <p role="alert" className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {!isLoading && !error ? (
        <div className="mt-6 space-y-6">
          {providerGroups.map((group) => {
            const groupProviders = providers.filter(
              (provider) => provider.kind === group.kind,
            );
            if (groupProviders.length === 0) {
              return null;
            }
            return (
              <fieldset key={group.kind}>
                <legend className="section-title">{group.title}</legend>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  {group.subtitle}
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {groupProviders.map((provider) => (
                    <ProviderOption
                      key={provider.provider_id}
                      provider={provider}
                      selected={selectedProviderId === provider.provider_id}
                      onChange={onChange}
                    />
                  ))}
                </div>
              </fieldset>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

function ProviderOption({
  provider,
  selected,
  onChange,
}: {
  provider: LLMProviderInfo;
  selected: boolean;
  onChange: (providerId: string) => void;
}) {
  return (
    <label
      className={`block rounded-2xl border p-4 transition ${
        provider.configured
          ? "cursor-pointer hover:border-moss/60"
          : "cursor-not-allowed bg-slate-50 opacity-60"
      } ${selected ? "border-moss bg-emerald-50 ring-2 ring-moss/10" : "border-slate-200 bg-white"}`}
    >
      <div className="flex items-start gap-3">
        <input
          type="radio"
          name="llm_provider"
          value={provider.provider_id}
          checked={selected}
          disabled={!provider.configured}
          onChange={() => onChange(provider.provider_id)}
          className="mt-1 h-4 w-4 accent-moss"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-semibold text-ink">{provider.display_name}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                provider.configured
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-slate-200 text-slate-600"
              }`}
            >
              {provider.configured ? "Configured" : "Not configured"}
            </span>
          </div>
          <p className="mt-1 font-mono text-xs text-moss">{provider.model_name}</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {provider.description}
          </p>
        </div>
      </div>
    </label>
  );
}
