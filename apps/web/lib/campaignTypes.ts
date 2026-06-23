export type ConversationRole = "user" | "assistant" | "system";

export interface ConversationMessage {
  role: ConversationRole;
  content: string;
}

export interface BrandProofPoint {
  claim: string;
  source?: string | null;
}

export interface BrandContext {
  target_personas?: string[] | null;
  proof_points?: BrandProofPoint[] | null;
  forbidden_words?: string[] | null;
  competitors?: string[] | null;
  tone_rules?: string[] | null;
  source_links?: string[] | null;
}

export interface CampaignGenerationRequest {
  product_name: string;
  product_description: string;
  target_audience: string;
  marketing_goal: string;
  brand_voice?: string | null;
  constraints?: string[] | null;
  user_prompt: string;
  conversation_history?: ConversationMessage[] | null;
  target_market?: string | null;
  output_language?: string | null;
  selected_channels?: string[] | null;
  campaign_duration?: string | null;
  campaign_template?: string | null;
  brand_context?: BrandContext | null;
}

export interface IdeationResult {
  campaign_concept: string;
  core_message: string;
  target_audience_insight: string;
  recommended_angles: string[];
  risks_or_assumptions: string[];
  follow_up_questions: string[];
  is_ready_for_planning: boolean;
}

export interface CampaignChannelPlan {
  channel_name: string;
  role_in_campaign: string;
  content_types: string[];
  key_messages: string[];
  cadence: string;
  success_metrics: string[];
}

export interface CampaignTimelineItem {
  phase_name: string;
  timing: string;
  objective: string;
  key_activities: string[];
}

export interface CampaignDeliverable {
  name: string;
  channel: string;
  format: string;
  purpose: string;
}

export interface MarketAdaptation {
  target_market: string;
  language_strategy: string;
  positioning_recommendations: string[];
  localization_notes: string[];
  cultural_risks: string[];
  suggested_phrases: string[];
}

export interface CampaignAsset {
  asset_type: string;
  channel: string;
  title: string;
  content: string;
  call_to_action: string;
  notes: string[];
}

export type CampaignClaimStatus = "source_backed" | "needs_validation";

export interface CampaignClaimCheck {
  claim: string;
  status: CampaignClaimStatus;
  source?: string | null;
}

export interface CampaignPlan {
  campaign_name: string;
  campaign_objective: string;
  target_audience: string;
  core_message: string;
  channels: CampaignChannelPlan[];
  content_pillars: string[];
  timeline: CampaignTimelineItem[];
  deliverables: CampaignDeliverable[];
  success_metrics: string[];
  assumptions: string[];
  execution_notes: string[];
  market_adaptation?: MarketAdaptation | null;
  draft_assets?: CampaignAsset[] | null;
  claim_checks?: CampaignClaimCheck[] | null;
}

export type CampaignWorkflowStatus =
  | "needs_more_ideation"
  | "plan_generated";

export interface CampaignWorkflowResponse {
  status: CampaignWorkflowStatus;
  ideation_result: IdeationResult;
  campaign_plan: CampaignPlan | null;
}

export type LLMProviderKind = "local" | "remote" | "development";

export interface LLMProviderInfo {
  provider_id: string;
  display_name: string;
  model_name: string;
  kind: LLMProviderKind;
  description: string;
  configured: boolean;
  is_default: boolean;
}

export interface LLMProviderCatalog {
  providers: LLMProviderInfo[];
}
