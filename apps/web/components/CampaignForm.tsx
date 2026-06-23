"use client";

import { FormEvent, useState } from "react";

import type {
  BrandContext,
  BrandProofPoint,
  CampaignGenerationRequest,
} from "@/lib/campaignTypes";

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
  campaign_template: string;
  target_personas: string;
  proof_points: string;
  forbidden_words: string;
  competitors: string;
  tone_rules: string;
  source_links: string;
}

const channelOptions = [
  "LinkedIn",
  "Email",
  "Landing Page",
  "X / Twitter",
  "Blog",
  "GitHub / CLI",
  "Community",
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
  campaign_template: "general",
  target_personas: "",
  proof_points: "",
  forbidden_words: "",
  competitors: "",
  tone_rules: "",
  source_links: "",
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
  campaign_template: "general",
  target_personas: "",
  proof_points: "",
  forbidden_words: "",
  competitors: "",
  tone_rules: "",
  source_links: "",
};

const testSpriteFields: CampaignFormFields = {
  product_name: "TestSprite",
  product_description:
    "An agentic testing platform for AI-native teams. TestSprite uses live browsers and APIs to verify AI-generated code, returns actionable failure bundles, and works across web app, CLI, IDE, MCP, and CI workflows.",
  target_audience:
    "Engineering leaders, AI-native developers, QA engineers, and founders using coding agents such as Codex, Cursor, Claude Code, and similar tools",
  marketing_goal:
    "Generate qualified developer signups, API key starts, and technical demo calls from teams adopting AI coding agents",
  brand_voice: "Technical, direct, evidence-led, developer-trust-first",
  constraints:
    "Do not overclaim autonomy\nUse source-backed proof\nShow CLI or live-app workflow\nAvoid generic AI productivity language",
  user_prompt:
    "ready for planning: create a developer-tool campaign for TestSprite that explains why AI coding agents need a verifier",
  target_market: "United States",
  output_language: "English",
  campaign_duration: "4 weeks",
  selected_channels: ["LinkedIn", "X / Twitter", "Blog", "GitHub / CLI", "Email", "Community"],
  campaign_template: "developer_tool",
  target_personas:
    "AI-native engineering teams\nEngineering leaders adopting coding agents\nQA engineers modernizing automated testing\nDeveloper-tool founders",
  proof_points:
    "TestSprite announced $6.7M in seed funding | https://www.geekwire.com/2025/seattle-startup-testsprite-raises-6-7m-to-become-testing-backbone-for-ai-generated-code/\nTestSprite says its user base grew from 6,000 to 35,000 in three months | https://www.geekwire.com/2025/seattle-startup-testsprite-raises-6-7m-to-become-testing-backbone-for-ai-generated-code/\nTestSprite CLI is open source and helps AI agents check their own work | https://siliconangle.com/2026/06/11/testsprite-launches-open-source-command-line-tool-help-ai-agents-check-work/\nTestSprite positions itself as agentic testing for AI-native teams | https://www.testsprite.com/",
  forbidden_words: "magic\nfully autonomous without review\nbug-free\nset and forget",
  competitors: "Playwright\nCypress\nSelenium\nQA Wolf\nRainforest QA",
  tone_rules:
    "Lead with the verification gap\nShow real workflow steps\nMark unsourced numeric claims as needs validation\nPrefer technical proof over hype",
  source_links:
    "https://www.testsprite.com/\nhttps://www.geekwire.com/2025/seattle-startup-testsprite-raises-6-7m-to-become-testing-backbone-for-ai-generated-code/\nhttps://siliconangle.com/2026/06/11/testsprite-launches-open-source-command-line-tool-help-ai-agents-check-work/",
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

    const constraints = splitLines(fields.constraints);
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
      campaign_template: fields.campaign_template,
      brand_context: buildBrandContext(fields),
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
          Phase 2.3
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

      <div className="grid gap-5 sm:grid-cols-4">
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
        <Field label="Campaign Template">
          <select
            id="campaign_template"
            className="input"
            value={fields.campaign_template}
            onChange={(event) => updateField("campaign_template", event.target.value)}
            disabled={isLoading}
          >
            <option value="general">General launch</option>
            <option value="developer_tool">Developer tool</option>
          </select>
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

      <section className="rounded-3xl border border-slate-200 bg-white/70 p-5">
        <div className="mb-5">
          <p className="eyebrow">Brand context</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">
            Add proof and guardrails for developer-trust copy
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Use this for TestSprite-style campaigns where sourced claims, precise personas, and forbidden wording matter.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Target Personas">
            <textarea
              id="target_personas"
              className="input min-h-24 resize-y"
              value={fields.target_personas}
              onChange={(event) => updateField("target_personas", event.target.value)}
              disabled={isLoading}
              placeholder="One persona per line"
            />
          </Field>
          <Field label="Proof Points">
            <textarea
              id="proof_points"
              className="input min-h-24 resize-y"
              value={fields.proof_points}
              onChange={(event) => updateField("proof_points", event.target.value)}
              disabled={isLoading}
              placeholder="Claim | source URL"
            />
          </Field>
          <Field label="Forbidden Words">
            <textarea
              id="forbidden_words"
              className="input min-h-20 resize-y"
              value={fields.forbidden_words}
              onChange={(event) => updateField("forbidden_words", event.target.value)}
              disabled={isLoading}
              placeholder="One word or phrase per line"
            />
          </Field>
          <Field label="Competitors">
            <textarea
              id="competitors"
              className="input min-h-20 resize-y"
              value={fields.competitors}
              onChange={(event) => updateField("competitors", event.target.value)}
              disabled={isLoading}
              placeholder="One competitor per line"
            />
          </Field>
          <Field label="Tone Rules">
            <textarea
              id="tone_rules"
              className="input min-h-20 resize-y"
              value={fields.tone_rules}
              onChange={(event) => updateField("tone_rules", event.target.value)}
              disabled={isLoading}
              placeholder="One tone rule per line"
            />
          </Field>
          <Field label="Source Links">
            <textarea
              id="source_links"
              className="input min-h-20 resize-y"
              value={fields.source_links}
              onChange={(event) => updateField("source_links", event.target.value)}
              disabled={isLoading}
              placeholder="One source URL per line"
            />
          </Field>
        </div>
      </section>

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
            setFields(testSpriteFields);
            setValidationError(null);
          }}
          disabled={isLoading}
        >
          Use TestSprite Demo
        </button>
        <button
          className="button-ghost"
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

function splitLines(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseProofPoints(value: string): BrandProofPoint[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [claim, ...sourceParts] = line.split("|");
      return {
        claim: claim.trim(),
        source: sourceParts.join("|").trim() || null,
      };
    })
    .filter((item) => item.claim);
}

function buildBrandContext(fields: CampaignFormFields): BrandContext | null {
  const context: BrandContext = {
    target_personas: nullIfEmpty(splitLines(fields.target_personas)),
    proof_points: nullIfEmpty(parseProofPoints(fields.proof_points)),
    forbidden_words: nullIfEmpty(splitLines(fields.forbidden_words)),
    competitors: nullIfEmpty(splitLines(fields.competitors)),
    tone_rules: nullIfEmpty(splitLines(fields.tone_rules)),
    source_links: nullIfEmpty(splitLines(fields.source_links)),
  };

  const hasContext = Object.values(context).some((value) => Array.isArray(value) && value.length > 0);
  return hasContext ? context : null;
}

function nullIfEmpty<T>(items: T[]): T[] | null {
  return items.length > 0 ? items : null;
}
