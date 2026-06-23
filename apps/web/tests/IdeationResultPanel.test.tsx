import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IdeationResultPanel } from "@/components/IdeationResultPanel";

describe("IdeationResultPanel", () => {
  it("shows follow-up questions as a non-error clarification state", () => {
    render(
      <IdeationResultPanel
        result={{
          campaign_concept: "A sharper founder launch",
          core_message: "Turn strategy into measurable momentum.",
          target_audience_insight: "Founders need practical proof.",
          recommended_angles: ["Show before and after"],
          risks_or_assumptions: ["Proof is available"],
          follow_up_questions: ["Which pain point should lead?"],
          is_ready_for_planning: false,
        }}
      />,
    );

    expect(screen.getByText("Needs clarification")).toBeInTheDocument();
    expect(screen.getByText("Which pain point should lead?")).toBeInTheDocument();
  });
});
