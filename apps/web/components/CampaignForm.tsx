"use client";

import { FormEvent, useState } from "react";

import type { CampaignGenerationRequest } from "@/lib/campaignTypes";

interface CampaignFormProps {
  onSubmit: (request: CampaignGenerationRequest) => void | Promise<void>;
  onClear?: () => void;
  isLoading: boolean;
}

interface CampaignFormFields {
  product_name: string;
  product_description: string;
  target_audience: string;
  marketing_goal: string;
  brand_voice: string;
  constraints: string;
  user_prompt: string;
}

const emptyFields: CampaignFormFields = {
  product_name: "",
  product_description: "",
  target_audience: "",
  marketing_goal: "",
  brand_voice: "",
  constraints: "",
  user_prompt: "",
};

const demoFields: CampaignFormFields = {
  product_name: "TensorGrowth",
  product_description:
    "An AI marketing workspace that helps founders generate and plan campaigns.",
  target_audience: "Early-stage startup founders and lean marketing teams",
  marketing_goal: "Generate qualified waitlist signups",
  brand_voice: "Sharp, practical, founder-friendly",
  constraints: "Small team\nLimited budget\nOrganic-first",
  user_prompt:
    "ready for planning: create a launch campaign concept for this product",
};

const requiredFields: Array<keyof CampaignFormFields> = [
  "product_name",
  "product_description",
  "target_audience",
  "marketing_goal",
  "user_prompt",
];

export function CampaignForm({
  onSubmit,
  onClear,
  isLoading,
}: CampaignFormProps) {
  const [fields, setFields] = useState<CampaignFormFields>(emptyFields);
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateField(name: keyof CampaignFormFields, value: string) {
    setFields((current) => ({ ...current, [name]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hasMissingRequiredField = requiredFields.some(
      (field) => !fields[field].trim(),
    );
    if (hasMissingRequiredField) {
      setValidationError("Complete all required fields before generating.");
      return;
    }

    const constraints = fields.constraints
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean);
    setValidationError(null);
    void onSubmit({
      product_name: fields.product_name.trim(),
      product_description: fields.product_description.trim(),
      target_audience: fields.target_audience.trim(),
      marketing_goal: fields.marketing_goal.trim(),
      brand_voice: fields.brand_voice.trim() || null,
      constraints: constraints.length > 0 ? constraints : null,
      user_prompt: fields.user_prompt.trim(),
      conversation_history: null,
    });
  }

  function handleClear() {
    setFields(emptyFields);
    setValidationError(null);
    onClear?.();
  }

  return (
    <form className="panel space-y-6" onSubmit={handleSubmit} noValidate>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Campaign brief</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">
            Define the opportunity
          </h2>
        </div>
        <span className="rounded-full bg-lime/40 px-3 py-1 text-xs font-semibold text-ink">
          Phase 2
        </span>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Product Name" required>
          <input
            id="product_name"
            className="input"
            value={fields.product_name}
            onChange={(event) => updateField("product_name", event.target.value)}
            disabled={isLoading}
          />
        </Field>
        <Field label="Brand Voice">
          <input
            id="brand_voice"
            className="input"
            value={fields.brand_voice}
            onChange={(event) => updateField("brand_voice", event.target.value)}
            disabled={isLoading}
            placeholder="Direct, optimistic, expert"
          />
        </Field>
      </div>

      <Field label="Product Description" required>
        <textarea
          id="product_description"
          className="input min-h-28 resize-y"
          value={fields.product_description}
          onChange={(event) =>
            updateField("product_description", event.target.value)
          }
          disabled={isLoading}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Target Audience" required>
          <textarea
            id="target_audience"
            className="input min-h-24 resize-y"
            value={fields.target_audience}
            onChange={(event) =>
              updateField("target_audience", event.target.value)
            }
            disabled={isLoading}
          />
        </Field>
        <Field label="Marketing Goal" required>
          <textarea
            id="marketing_goal"
            className="input min-h-24 resize-y"
            value={fields.marketing_goal}
            onChange={(event) =>
              updateField("marketing_goal", event.target.value)
            }
            disabled={isLoading}
          />
        </Field>
      </div>

      <Field label="Constraints">
        <textarea
          id="constraints"
          className="input min-h-24 resize-y"
          value={fields.constraints}
          onChange={(event) => updateField("constraints", event.target.value)}
          disabled={isLoading}
          placeholder="One item per line, or comma separated"
        />
      </Field>

      <Field label="User Prompt" required>
        <textarea
          id="user_prompt"
          className="input min-h-28 resize-y"
          value={fields.user_prompt}
          onChange={(event) => updateField("user_prompt", event.target.value)}
          disabled={isLoading}
          placeholder="Describe the campaign direction you want to explore."
        />
      </Field>

      {validationError ? (
        <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {validationError}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <button className="button-primary" type="submit" disabled={isLoading}>
          {isLoading ? "Generating…" : "Generate Campaign"}
        </button>
        <button
          className="button-secondary"
          type="button"
          onClick={() => {
            setFields(demoFields);
            setValidationError(null);
          }}
          disabled={isLoading}
        >
          Use Demo Input
        </button>
        <button
          className="button-ghost"
          type="button"
          onClick={handleClear}
          disabled={isLoading}
        >
          Clear
        </button>
      </div>
    </form>
  );
}

interface FieldProps {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}

function Field({ label, required = false, children }: FieldProps) {
  const id = label.toLowerCase().replaceAll(" ", "_");
  return (
    <div className="space-y-2">
      <label className="label" htmlFor={id}>
        {label}
        {required ? (
          <span aria-hidden="true" className="ml-1 text-coral">
            *
          </span>
        ) : null}
      </label>
      {children}
    </div>
  );
}
