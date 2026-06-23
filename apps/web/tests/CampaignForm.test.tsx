import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CampaignForm } from "@/components/CampaignForm";

describe("CampaignForm", () => {
  it("does not submit when required fields are empty", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<CampaignForm onSubmit={onSubmit} isLoading={false} />);

    await user.click(screen.getByRole("button", { name: "Generate Campaign Package" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Complete all required fields before generating.",
    );
  });

  it("fills a deterministic planning-ready demo brief", async () => {
    const user = userEvent.setup();
    render(<CampaignForm onSubmit={vi.fn()} isLoading={false} />);

    await user.click(screen.getByRole("button", { name: "Use Demo Input" }));

    expect(screen.getByRole("textbox", { name: "Product Name" })).toHaveValue(
      "TensorGrowth",
    );
    expect(screen.getByRole("textbox", { name: "Target Market" })).toHaveValue(
      "United States",
    );
    expect(screen.getByRole("combobox", { name: "Output Language" })).toHaveValue(
      "English",
    );
    expect(screen.getByRole("combobox", { name: "Campaign Template" })).toHaveValue(
      "general",
    );
    expect(screen.getByRole("textbox", { name: "User Prompt" })).toHaveValue(
      "ready for planning: create a launch campaign concept for this product",
    );
    expect(screen.getByLabelText("Constraints")).toHaveValue(
      "Small team\nLimited budget\nOrganic-first",
    );
  });

  it("fills a TestSprite developer-tool demo with proof points", async () => {
    const user = userEvent.setup();
    render(<CampaignForm onSubmit={vi.fn()} isLoading={false} />);

    await user.click(screen.getByRole("button", { name: "Use TestSprite Demo" }));

    expect(screen.getByRole("textbox", { name: "Product Name" })).toHaveValue(
      "TestSprite",
    );
    expect(screen.getByRole("combobox", { name: "Campaign Template" })).toHaveValue(
      "developer_tool",
    );
    expect(screen.getByLabelText("Proof Points")).toHaveValue(
      expect.any(String),
    );
    expect(String(screen.getByLabelText("Proof Points").getAttribute("value") ?? screen.getByLabelText("Proof Points").textContent ?? "")).toContain(
      "$6.7M in seed funding",
    );
    expect(screen.getByLabelText("Forbidden Words")).toHaveValue(
      expect.any(String),
    );
    expect(String(screen.getByLabelText("Forbidden Words").getAttribute("value") ?? screen.getByLabelText("Forbidden Words").textContent ?? "")).toContain(
      "bug-free",
    );
  });

  it("normalizes brand context and selected channels before submitting", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<CampaignForm onSubmit={onSubmit} isLoading={false} />);

    await user.click(screen.getByRole("button", { name: "Use TestSprite Demo" }));
    await user.click(screen.getByRole("button", { name: "Generate Campaign Package" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        product_name: "TestSprite",
        campaign_template: "developer_tool",
        selected_channels: ["LinkedIn", "X / Twitter", "Blog", "GitHub / CLI", "Email", "Community"],
        target_market: "United States",
        output_language: "English",
        brand_context: expect.objectContaining({
          target_personas: expect.arrayContaining(["AI-native engineering teams"]),
          forbidden_words: expect.arrayContaining(["bug-free"]),
          proof_points: expect.arrayContaining([
            expect.objectContaining({
              claim: "TestSprite announced $6.7M in seed funding",
              source: expect.stringContaining("geekwire.com"),
            }),
          ]),
        }),
      }),
    );
  });
});
