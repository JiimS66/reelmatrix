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
  target_market: string;
  output_language: string;
  campaign_duration: string;
  selected_channels: string[];
}

const channelOptions = [
  "LinkedIn",
  "Email",
  "Landing Page",
  "X / Twitter",
  "Blog",
] as const;

const emptyFields: CampaignFormFields = {
  product_name: "",
  product_description: "",
  target_audience: "",
  marketing_goal: "",
  brand_voice: "",
  constraints: "",
  user_prompt: "",
  target_market: "United States",
  output_language: "English",
  campaign_duration: "4 weeks",
  selected_channels: ["LinkedIn", "Email", "Landing Page"],
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
  target_market: "United States",
  output_language: "English",
  campaign_duration: "4 weeks",
  selected_channels: ["LinkedIn", "Email", "Landing Page"],
};

const requiredFields: Array<keyof CampaignFormFields> = [
  "product_name",
  "product_description",
  "target_audience",
  "marketing_goal",
  "user_prompt",
  "target_market",
  "output_language",
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

  function toggleChannel(channel: string) {
    setFields((current) => {
      const selected = current.selected_channels.includes(channel)
        ? current.selected_channels.filter((item) => item !== channel)
        : [...current.selected_channels, channel];
      return { ...current, selected_channels: selected };
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hasMissingRequiredField = requiredFields.some(
      (field) => !String(fields[field]).trim(),
    );
    if (hasMissingRequiredField) {
      setValidationError("Complete all required fields before generating.");
      return;
    }
    if (fields.selected_channels.length === 0) {
      setValidationError("Choose at least one campaign channel.");
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
      target_market: fields.target_market.trim(),
      output_language: fields.output_language.trim(),
      selected_channels: fields.selected_channels,
      campaign_duration: fields.campaign_duration.trim() || null,
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
            Define the cross-border opportunity
          </h2>
        </div>
        <span className="rounded-full bg-lime/40 px-3 py-1 text-xs font-semibold text-ink">
          Phase 2.1
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

      <div className="grid gap-5 sm:grid-cols-3">
        <Field label="Target Market" required>
          <input
            id="target_market"
            className="input"
            value={fields.target_market}
            onChange={(event) => updateField("target_market", event.target.value)}
            disabled={isLoading}
            placeholder="United States, Europe, SEA"
          />
        </Field>
        <Field label="Output Language" required>
          <select
            id="output_language"
            className="input"
            value={fields.output_language}
            onChange={(event) => updateField("output_language", event.target.value)}
            disabled={isLoading}
          >
            <option>English</option>
            <option>Chinese</option>
            <option>Chinese + English</option>
          </select>
        </Field>
        <Field label="Campaign Duration">
          <input
            id="campaign_duration"
            className="input"
            value={fields.campaign_duration}
            onChange={(event) => updateField("campaign_duration", event.target.value)}
            disabled={isLoading}
            placeholder="4 weeks"
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

      <fieldset>
        <legend className="label">Campaign Channels</legend>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {channelOptions.map((channel) => (
            <label
              key={channel}
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-ink"
            >
              <input
                type="checkbox"
                className="h-4 w-4 accent-moss"
                checked={fields.selected_channels.includes(channel)}
                onChange={() => toggleChannel(channel)}
                disabled={isLoading}
              />
              {channel}
            </label>
          ))}
        </div>
      </fieldset>

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
          {isLoading ? "Generating..." : "Generate Campaign Package"}
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
