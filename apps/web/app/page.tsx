"use client";

import { useEffect, useState } from "react";

import { CampaignForm } from "@/components/CampaignForm";
import { CampaignPackageWorkspace } from "@/components/CampaignPackageWorkspace";
import { ErrorState } from "@/components/ErrorState";
import { FollowUpPanel } from "@/components/FollowUpPanel";
import { IdeationResultPanel } from "@/components/IdeationResultPanel";
import { LoadingState } from "@/components/LoadingState";
import { ModelSelector } from "@/components/ModelSelector";
import {
  CampaignApiError,
  generateCampaign,
  getLLMProviders,
} from "@/lib/api";
import type {
  CampaignGenerationRequest,
  CampaignWorkflowResponse,
  ConversationMessage,
  IdeationResult,
  LLMProviderInfo,
} from "@/lib/campaignTypes";

export default function Home() {
  const [result, setResult] = useState<CampaignWorkflowResponse | null>(null);
  const [lastRequest, setLastRequest] =
    useState<CampaignGenerationRequest | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [lastProviderId, setLastProviderId] = useState<string | null>(null);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [providerError, setProviderError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    getLLMProviders()
      .then((catalog) => {
        if (!isActive) {
          return;
        }
        setProviders(catalog.providers);
        const defaultProvider = catalog.providers.find(
          (provider) => provider.is_default && provider.configured,
        );
        const firstConfiguredProvider = catalog.providers.find(
          (provider) => provider.configured,
        );
        setSelectedProviderId(
          defaultProvider?.provider_id ?? firstConfiguredProvider?.provider_id ?? "",
        );
      })
      .catch((caughtError: unknown) => {
        if (!isActive) {
          return;
        }
        setProviderError(
          caughtError instanceof CampaignApiError
            ? caughtError.message
            : "Unable to load model providers.",
        );
      })
      .finally(() => {
        if (isActive) {
          setIsLoadingProviders(false);
        }
      });
    return () => {
      isActive = false;
    };
  }, []);

  async function submitRequest(
    request: CampaignGenerationRequest,
    providerId: string = selectedProviderId,
  ) {
    if (!providerId) {
      setError("Choose a configured model provider before generating.");
      return;
    }
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await generateCampaign(request, providerId);
      setLastRequest(request);
      setLastProviderId(providerId);
      setResult(response);
    } catch (caughtError) {
      setError(
        caughtError instanceof CampaignApiError
          ? caughtError.message
          : "An unexpected error interrupted campaign generation.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function submitFollowUp(answer: string) {
    if (!lastRequest || !result || !lastProviderId) {
      return;
    }
    const conversationHistory = buildConversationHistory(
      lastRequest,
      result.ideation_result,
      answer,
    );
    await submitRequest(
      {
        ...lastRequest,
        user_prompt: answer,
        conversation_history: conversationHistory,
      },
      lastProviderId,
    );
  }

  function clearWorkspace() {
    setResult(null);
    setLastRequest(null);
    setLastProviderId(null);
    setError(null);
  }

  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 overflow-hidden rounded-[2rem] bg-ink px-6 py-8 text-white shadow-card sm:px-10 sm:py-10">
          <div className="max-w-4xl">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-lime">
              ReelMatrix / AI Campaign Studio
            </p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
              Build the first cross-border campaign package before your next standup.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-white/70">
              Enter your product, market, channels, and goal. Choose local, Qwen,
              or GPT, then generate an editable campaign plan, localization notes,
              and first-draft channel materials for a small team to execute.
            </p>
          </div>
        </header>

        <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)]">
          <div className="xl:sticky xl:top-6">
            <ModelSelector
              providers={providers}
              selectedProviderId={selectedProviderId}
              onChange={setSelectedProviderId}
              isLoading={isLoadingProviders}
              error={providerError}
            />
            <CampaignForm
              onSubmit={submitRequest}
              onClear={clearWorkspace}
              isLoading={isLoading || isLoadingProviders || !selectedProviderId}
            />
          </div>

          <div className="space-y-6" aria-live="polite">
            {!result && !error && !isLoading ? <EmptyResult /> : null}
            {isLoading ? <LoadingState /> : null}
            {error ? <ErrorState message={error} /> : null}
            {result ? <IdeationResultPanel result={result.ideation_result} /> : null}
            {result?.status === "needs_more_ideation" ? (
              <FollowUpPanel
                questions={result.ideation_result.follow_up_questions}
                onSubmit={submitFollowUp}
                isLoading={isLoading}
              />
            ) : null}
            {result?.status === "plan_generated" && result.campaign_plan ? (
              <CampaignPackageWorkspace plan={result.campaign_plan} />
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}

function buildConversationHistory(
  request: CampaignGenerationRequest,
  ideation: IdeationResult,
  answer: string,
): ConversationMessage[] {
  const history = [...(request.conversation_history ?? [])];
  const latestMessage = history.at(-1);
  if (
    !latestMessage ||
    latestMessage.role !== "user" ||
    latestMessage.content !== request.user_prompt
  ) {
    history.push({ role: "user", content: request.user_prompt });
  }
  history.push({
    role: "assistant",
    content: [
      `Campaign concept: ${ideation.campaign_concept}`,
      `Core message: ${ideation.core_message}`,
      `Follow-up questions: ${ideation.follow_up_questions.join(" | ")}`,
    ].join("\n"),
  });
  history.push({ role: "user", content: answer });
  return history;
}

function EmptyResult() {
  return (
    <section className="panel border-dashed bg-white/55 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-lime text-xl font-bold text-ink">
        R
      </div>
      <h2 className="mt-4 text-xl font-semibold text-ink">
        Your campaign package appears here
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">
        Submit a complete brief or load the demo input to see the plan, market
        adaptation, and editable channel assets.
      </p>
    </section>
  );
}
