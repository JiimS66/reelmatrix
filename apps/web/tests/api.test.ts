import { afterEach, describe, expect, it, vi } from "vitest";

import {
  CampaignApiError,
  generateCampaign,
  getLLMProviders,
} from "@/lib/api";
import type {
  CampaignGenerationRequest,
  CampaignWorkflowResponse,
} from "@/lib/campaignTypes";

const request: CampaignGenerationRequest = {
  product_name: "TensorGrowth",
  product_description: "An AI marketing workspace for lean marketing teams.",
  target_audience: "Early-stage startup founders",
  marketing_goal: "Generate qualified waitlist signups",
  user_prompt: "ready for planning",
};

const responseBody: CampaignWorkflowResponse = {
  status: "needs_more_ideation",
  ideation_result: {
    campaign_concept: "Clarify the launch idea",
    core_message: "The promise needs more specificity.",
    target_audience_insight: "Founders need practical proof.",
    recommended_angles: ["Lead with the highest-cost problem"],
    risks_or_assumptions: ["The pain point needs validation"],
    follow_up_questions: ["What proof can support the promise?"],
    is_ready_for_planning: false,
  },
  campaign_plan: null,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("generateCampaign", () => {
  it("returns a successful workflow response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(generateCampaign(request)).resolves.toEqual(responseBody);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/campaign/generate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("sends the selected provider in a request header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await generateCampaign(request, "dashscope");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/campaign/generate",
      expect.objectContaining({
        headers: {
          "Content-Type": "application/json",
          "X-LLM-Provider": "dashscope",
        },
      }),
    );
  });

  it("maps HTTP 422 to a user-readable validation error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 422 })));

    await expect(generateCampaign(request)).rejects.toMatchObject({
      message: "The request was rejected by the API. Please check required fields.",
      status: 422,
    });
  });

  it("maps HTTP 502 to a model provider error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 502 })));

    await expect(generateCampaign(request)).rejects.toMatchObject({
      message:
        "The model provider failed or returned invalid structured output. Please retry or use mock provider.",
      status: 502,
    });
  });

  it("maps HTTP 503 to an unconfigured provider error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await expect(generateCampaign(request, "openai")).rejects.toMatchObject({
      message: "The selected model provider is not configured on the backend.",
      status: 503,
    });
  });

  it("maps network failures without leaking the underlying error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    await expect(generateCampaign(request)).rejects.toEqual(
      new CampaignApiError(
        "Cannot reach the backend API. Check NEXT_PUBLIC_API_BASE_URL and backend server.",
      ),
    );
  });
});

describe("getLLMProviders", () => {
  it("loads the provider catalog", async () => {
    const catalog = {
      providers: [
        {
          provider_id: "dashscope",
          display_name: "Qwen",
          model_name: "qwen-plus",
          kind: "remote",
          description: "Remote Qwen model",
          configured: true,
          is_default: true,
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(catalog), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(getLLMProviders()).resolves.toEqual(catalog);
  });
});
