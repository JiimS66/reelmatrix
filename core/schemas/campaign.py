from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmptyStr = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1),
]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(StrictSchema):
    role: ConversationRole
    content: NonEmptyStr


class BrandProofPoint(StrictSchema):
    claim: NonEmptyStr
    source: Optional[NonEmptyStr] = None


class BrandContext(StrictSchema):
    target_personas: Optional[List[NonEmptyStr]] = None
    proof_points: Optional[List[BrandProofPoint]] = None
    forbidden_words: Optional[List[NonEmptyStr]] = None
    competitors: Optional[List[NonEmptyStr]] = None
    tone_rules: Optional[List[NonEmptyStr]] = None
    source_links: Optional[List[NonEmptyStr]] = None


class CampaignGenerationRequest(StrictSchema):
    product_name: NonEmptyStr
    product_description: NonEmptyStr
    target_audience: NonEmptyStr
    marketing_goal: NonEmptyStr
    brand_voice: Optional[NonEmptyStr] = None
    constraints: Optional[List[NonEmptyStr]] = None
    user_prompt: NonEmptyStr
    conversation_history: Optional[List[ConversationMessage]] = None
    target_market: Optional[NonEmptyStr] = None
    output_language: Optional[NonEmptyStr] = None
    selected_channels: Optional[List[NonEmptyStr]] = None
    campaign_duration: Optional[NonEmptyStr] = None
    campaign_template: Optional[NonEmptyStr] = None
    brand_context: Optional[BrandContext] = None


class IdeationResult(StrictSchema):
    campaign_concept: NonEmptyStr
    core_message: NonEmptyStr
    target_audience_insight: NonEmptyStr
    recommended_angles: List[NonEmptyStr] = Field(min_length=1)
    risks_or_assumptions: List[NonEmptyStr]
    follow_up_questions: List[NonEmptyStr]
    is_ready_for_planning: bool


class CampaignChannelPlan(StrictSchema):
    channel_name: NonEmptyStr
    role_in_campaign: NonEmptyStr
    content_types: List[NonEmptyStr] = Field(min_length=1)
    key_messages: List[NonEmptyStr] = Field(min_length=1)
    cadence: NonEmptyStr
    success_metrics: List[NonEmptyStr] = Field(min_length=1)


class CampaignTimelineItem(StrictSchema):
    phase_name: NonEmptyStr
    timing: NonEmptyStr
    objective: NonEmptyStr
    key_activities: List[NonEmptyStr] = Field(min_length=1)


class CampaignDeliverable(StrictSchema):
    name: NonEmptyStr
    channel: NonEmptyStr
    format: NonEmptyStr
    purpose: NonEmptyStr


class MarketAdaptation(StrictSchema):
    target_market: NonEmptyStr
    language_strategy: NonEmptyStr
    positioning_recommendations: List[NonEmptyStr] = Field(min_length=1)
    localization_notes: List[NonEmptyStr] = Field(min_length=1)
    cultural_risks: List[NonEmptyStr]
    suggested_phrases: List[NonEmptyStr] = Field(min_length=1)


class CampaignAsset(StrictSchema):
    asset_type: NonEmptyStr
    channel: NonEmptyStr
    title: NonEmptyStr
    content: NonEmptyStr
    call_to_action: NonEmptyStr
    notes: List[NonEmptyStr]


class AuditDimension(str, Enum):
    BRAND_TONE = "brand_tone"
    UNSOURCED_CLAIM = "unsourced_claim"
    CONSISTENCY = "consistency"
    CLARITY = "clarity"


class AuditIssue(StrictSchema):
    dimension: AuditDimension
    detail: NonEmptyStr


class AuditVerdict(StrictSchema):
    """An LLM-as-judge verdict on a rendered post — the semantic layer above the
    deterministic format/brand/consistency checks. Run by an Auditor on a different
    model family than the generator, so their errors decorrelate."""

    approved: bool
    issues: List[AuditIssue] = Field(default_factory=list)


class ClaimStatus(str, Enum):
    SOURCE_BACKED = "source_backed"
    NEEDS_VALIDATION = "needs_validation"


class CampaignClaimCheck(StrictSchema):
    claim: NonEmptyStr
    status: ClaimStatus
    source: Optional[NonEmptyStr] = None


class CampaignPlan(StrictSchema):
    campaign_name: NonEmptyStr
    campaign_objective: NonEmptyStr
    target_audience: NonEmptyStr
    core_message: NonEmptyStr
    channels: List[CampaignChannelPlan] = Field(min_length=1)
    content_pillars: List[NonEmptyStr] = Field(min_length=1)
    timeline: List[CampaignTimelineItem] = Field(min_length=1)
    deliverables: List[CampaignDeliverable] = Field(min_length=1)
    success_metrics: List[NonEmptyStr] = Field(min_length=1)
    assumptions: List[NonEmptyStr]
    execution_notes: List[NonEmptyStr]
    market_adaptation: Optional[MarketAdaptation] = None
    draft_assets: Optional[List[CampaignAsset]] = None
    claim_checks: Optional[List[CampaignClaimCheck]] = None
    timely_angles: Optional[List[NonEmptyStr]] = None


class CampaignWorkflowStatus(str, Enum):
    NEEDS_MORE_IDEATION = "needs_more_ideation"
    PLAN_GENERATED = "plan_generated"


class CampaignWorkflowResponse(StrictSchema):
    status: CampaignWorkflowStatus
    ideation_result: IdeationResult
    campaign_plan: Optional[CampaignPlan]

    @model_validator(mode="after")
    def validate_plan_for_status(self) -> "CampaignWorkflowResponse":
        if (
            self.status == CampaignWorkflowStatus.NEEDS_MORE_IDEATION
            and self.campaign_plan is not None
        ):
            raise ValueError("campaign_plan must be null when more ideation is needed")
        if (
            self.status == CampaignWorkflowStatus.PLAN_GENERATED
            and self.campaign_plan is None
        ):
            raise ValueError("campaign_plan is required when a plan is generated")
        return self
