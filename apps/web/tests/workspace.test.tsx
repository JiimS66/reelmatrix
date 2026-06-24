import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ATOM_KIND_LABEL,
  CHECK_LABEL,
  CheckBadges,
  KIND_LABEL,
  MODE_LABEL,
  StatusBadge,
  cap,
  checkCount,
} from "@/components/workspace/primitives";
import type { Task } from "@/lib/teamApi";

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: "t1",
    campaign_id: "c1",
    kind: "asset",
    title: "LinkedIn asset",
    status: "needs_review",
    execution_mode: "ai_draft_human_review",
    assignee_id: null,
    depends_on: [],
    sequence: 1,
    params: {},
    output: null,
    checks: {},
    due_date: null,
    phase: null,
    updated_at: "2026-06-24",
    ...overrides,
  };
}

describe("workspace primitives", () => {
  it("capitalizes and maps labels", () => {
    expect(cap("ideation")).toBe("Ideation");
    expect(KIND_LABEL.claim_check).toBe("Claim check");
    expect(KIND_LABEL.visual).toBe("Visual");
    expect(MODE_LABEL.ai_auto).toBe("AI auto");
    expect(ATOM_KIND_LABEL.cta).toBe("CTA");
    expect(CHECK_LABEL.audit).toBe("Audit");
    expect(CHECK_LABEL.brand_fit).toBe("Brand fit");
  });

  it("counts check issues across groups", () => {
    const t = task({
      checks: { format: [{ code: "too_long", detail: "x" }], brand: [] },
    });
    expect(checkCount(t)).toBe(1);
  });

  it("renders a human-readable status", () => {
    render(<StatusBadge status="needs_review" />);
    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });

  it("renders format and brand check badges", () => {
    const t = task({
      checks: { format: [], brand: [{ code: "forbidden_word", detail: "x" }] },
    });
    render(<CheckBadges task={t} />);
    expect(screen.getByText(/Format/)).toBeInTheDocument();
    expect(screen.getByText(/Brand/)).toBeInTheDocument();
  });

  it("labels the auditor verdict as an Audit check", () => {
    const t = task({ checks: { audit: [{ code: "brand_tone", detail: "x" }] } });
    render(<CheckBadges task={t} />);
    expect(screen.getByText(/Audit/)).toBeInTheDocument();
  });
});
