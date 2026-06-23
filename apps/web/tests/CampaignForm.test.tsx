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
    expect(screen.getByRole("textbox", { name: "User Prompt" })).toHaveValue(
      "ready for planning: create a launch campaign concept for this product",
    );
    expect(screen.getByLabelText("Constraints")).toHaveValue(
      "Small team\nLimited budget\nOrganic-first",
    );
  });

  it("normalizes constraints and selected channels before submitting", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<CampaignForm onSubmit={onSubmit} isLoading={false} />);

    await user.click(screen.getByRole("button", { name: "Use Demo Input" }));
    await user.click(screen.getByRole("button", { name: "Generate Campaign Package" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        constraints: ["Small team", "Limited budget", "Organic-first"],
        selected_channels: ["LinkedIn", "Email", "Landing Page"],
        target_market: "United States",
        output_language: "English",
      }),
    );
  });
});
