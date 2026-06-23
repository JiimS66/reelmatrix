import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ModelSelector } from "@/components/ModelSelector";
import type { LLMProviderInfo } from "@/lib/campaignTypes";

const providers: LLMProviderInfo[] = [
  {
    provider_id: "local",
    display_name: "Local model",
    model_name: "llama3.1",
    kind: "local",
    description: "Local OpenAI-compatible model",
    configured: true,
    is_default: false,
  },
  {
    provider_id: "openai",
    display_name: "ChatGPT",
    model_name: "gpt-4o-mini",
    kind: "remote",
    description: "OpenAI hosted model",
    configured: false,
    is_default: false,
  },
  {
    provider_id: "dashscope",
    display_name: "Qwen",
    model_name: "qwen-plus",
    kind: "remote",
    description: "Alibaba Cloud hosted model",
    configured: true,
    is_default: true,
  },
];

describe("ModelSelector", () => {
  it("groups local and remote models and disables unconfigured providers", () => {
    render(
      <ModelSelector
        providers={providers}
        selectedProviderId="dashscope"
        onChange={vi.fn()}
        isLoading={false}
        error={null}
      />,
    );

    expect(screen.getByText("Local model", { selector: "legend" })).toBeInTheDocument();
    expect(screen.getByText("Remote models", { selector: "legend" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /ChatGPT/ })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /Qwen/ })).toBeChecked();
  });

  it("reports a configured provider selection", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ModelSelector
        providers={providers}
        selectedProviderId="dashscope"
        onChange={onChange}
        isLoading={false}
        error={null}
      />,
    );

    await user.click(screen.getByRole("radio", { name: /Local model/ }));

    expect(onChange).toHaveBeenCalledWith("local");
  });
});
