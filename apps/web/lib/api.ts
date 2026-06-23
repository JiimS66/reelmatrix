import type {
  CampaignGenerationRequest,
  CampaignWorkflowResponse,
  LLMProviderCatalog,
} from "@/lib/campaignTypes";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export class CampaignApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "CampaignApiError";
  }
}

function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(
    /\/$/,
    "",
  );
}

export async function generateCampaign(
  request: CampaignGenerationRequest,
  providerId?: string,
): Promise<CampaignWorkflowResponse> {
  let response: Response;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (providerId) {
    headers["X-LLM-Provider"] = providerId;
  }

  try {
    response = await fetch(`${getApiBaseUrl()}/api/v1/campaign/generate`, {
      method: "POST",
      headers,
      body: JSON.stringify(request),
    });
  } catch {
    throw new CampaignApiError(
      "Cannot reach the backend API. Check NEXT_PUBLIC_API_BASE_URL and backend server.",
    );
  }

  if (response.status === 422) {
    throw new CampaignApiError(
      "The request was rejected by the API. Please check required fields.",
      422,
    );
  }

  if (response.status === 502) {
    throw new CampaignApiError(
      "The model provider failed or returned invalid structured output. Please retry or use mock provider.",
      502,
    );
  }

  if (response.status === 503) {
    throw new CampaignApiError(
      "The selected model provider is not configured on the backend.",
      503,
    );
  }

  if (response.status === 400) {
    throw new CampaignApiError(
      "The selected model provider is not supported by the backend.",
      400,
    );
  }

  if (!response.ok) {
    throw new CampaignApiError(
      `The backend API returned an unexpected error (${response.status}).`,
      response.status,
    );
  }

  try {
    return (await response.json()) as CampaignWorkflowResponse;
  } catch {
    throw new CampaignApiError(
      "The backend API returned an unreadable response.",
      response.status,
    );
  }
}

export async function getLLMProviders(): Promise<LLMProviderCatalog> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/api/v1/llm/providers`, {
      method: "GET",
    });
  } catch {
    throw new CampaignApiError(
      "Cannot load model providers. Check the backend server and API base URL.",
    );
  }

  if (!response.ok) {
    throw new CampaignApiError(
      `The provider catalog request failed (${response.status}).`,
      response.status,
    );
  }

  try {
    return (await response.json()) as LLMProviderCatalog;
  } catch {
    throw new CampaignApiError(
      "The backend returned an unreadable provider catalog.",
      response.status,
    );
  }
}
