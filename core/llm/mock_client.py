import json
from typing import Any, Dict, List, Type

from core.llm.base import BaseLLMClient, LLMResponseValidationError, StructuredModel


class MockLLMClient(BaseLLMClient):
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return "Deterministic mock LLM response."

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[StructuredModel],
    ) -> StructuredModel:
        payload = self._parse_prompt_payload(user_prompt)
        builders = {
            "IdeationResult": self._build_ideation_result,
            "CampaignPlan": self._build_campaign_plan,
        }
        builder = builders.get(response_model.__name__)
        if builder is None:
            raise LLMResponseValidationError(
                f"MockLLMClient has no deterministic response for {response_model.__name__}"
            )
        return self.validate_object_response(builder(payload), response_model)

    @staticmethod
    def _parse_prompt_payload(user_prompt: str) -> Dict[str, Any]:
        try:
            payload = json.loads(user_prompt)
        except json.JSONDecodeError as exc:
            raise LLMResponseValidationError(
                "MockLLMClient expected the agent user prompt to be valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise LLMResponseValidationError(
                "MockLLMClient expected a JSON object prompt payload"
            )
        return payload

    @staticmethod
    def _build_ideation_result(payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        prompt = str(request.get("user_prompt", ""))
        combined = " ".join(
            str(request.get(field, ""))
            for field in (
                "product_description",
                "target_audience",
                "marketing_goal",
                "user_prompt",
            )
        ).lower()
        incomplete_markers = ("needs more ideation", "unknown", "tbd", "not sure")
        explicitly_incomplete = "needs more ideation" in prompt.lower()
        explicitly_ready = "ready for planning" in prompt.lower()
        sufficiently_detailed = (
            len(str(request.get("product_description", ""))) >= 20
            and len(str(request.get("target_audience", ""))) >= 12
            and len(str(request.get("marketing_goal", ""))) >= 12
            and not any(marker in combined for marker in incomplete_markers[1:])
        )
        is_ready = not explicitly_incomplete and (explicitly_ready or sufficiently_detailed)
        product_name = str(request.get("product_name", "the product"))
        audience = str(request.get("target_audience", "the target audience"))
        goal = str(request.get("marketing_goal", "the campaign goal"))

        if not is_ready:
            return {
                "campaign_concept": f"Clarify the strongest launch idea for {product_name}.",
                "core_message": "The campaign promise needs more evidence and specificity.",
                "target_audience_insight": f"More detail is needed about {audience} and their buying trigger.",
                "recommended_angles": [
                    "Lead with the audience's highest-cost current problem",
                    "Demonstrate a concrete before-and-after outcome",
                ],
                "risks_or_assumptions": [
                    "The primary pain point has not been validated",
                    "The desired conversion action may be too broad",
                ],
                "follow_up_questions": [
                    "What single pain point should this campaign prioritize?",
                    "What proof or customer evidence can support the campaign promise?",
                    "What exact action should the audience take after seeing the campaign?",
                ],
                "is_ready_for_planning": False,
            }

        return {
            "campaign_concept": f"The Lean Growth Launch for {product_name}",
            "core_message": f"Turn a clear product story into measurable marketing momentum toward {goal}.",
            "target_audience_insight": f"{audience} need credible, practical progress without adding operational overhead.",
            "recommended_angles": [
                "Replace fragmented campaign work with one guided workflow",
                "Show measurable progress for a resource-constrained team",
                "Use founder-relevant examples instead of generic AI claims",
            ],
            "risks_or_assumptions": [
                "The audience already recognizes campaign planning as a bottleneck",
                "Organic proof can establish enough trust for the initial conversion",
            ],
            "follow_up_questions": [],
            "is_ready_for_planning": True,
        }

    @staticmethod
    def _build_campaign_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        ideation = payload.get("ideation_result", {})
        product_name = str(request.get("product_name", "Product"))
        marketing_goal = str(request.get("marketing_goal", "Generate qualified demand"))
        target_audience = str(request.get("target_audience", "Target buyers"))
        target_market = str(request.get("target_market") or "United States")
        output_language = str(request.get("output_language") or "English")
        campaign_duration = str(request.get("campaign_duration") or "4 weeks")
        selected_channels = MockLLMClient._selected_channels(request)
        core_message = str(ideation.get("core_message", "Create measurable marketing momentum."))

        return {
            "campaign_name": f"{product_name} Cross-Border Launch Sprint",
            "campaign_objective": marketing_goal,
            "target_audience": target_audience,
            "core_message": core_message,
            "channels": MockLLMClient._build_channel_plans(
                selected_channels,
                core_message,
                campaign_duration,
            ),
            "content_pillars": [
                "The cost of fragmented campaign work",
                "Practical AI workflows for lean marketing teams",
                "Proof that a small team can move faster without adding headcount",
            ],
            "timeline": [
                {
                    "phase_name": "Foundation",
                    "timing": "Week 1",
                    "objective": "Establish the problem and campaign promise",
                    "key_activities": [
                        "Publish the category narrative",
                        "Finalize the landing-page hero message",
                    ],
                },
                {
                    "phase_name": "Activation",
                    "timing": "Weeks 2-3",
                    "objective": "Drive qualified prospects to the waitlist",
                    "key_activities": [
                        "Publish proof-led social content",
                        "Run the email launch sequence",
                    ],
                },
                {
                    "phase_name": "Learning loop",
                    "timing": "Week 4",
                    "objective": "Identify the message that creates the strongest intent",
                    "key_activities": [
                        "Compare channel engagement",
                        "Refine the strongest angle for the next sprint",
                    ],
                },
            ],
            "deliverables": [
                {
                    "name": "Founder launch narrative",
                    "channel": "LinkedIn",
                    "format": "Text post",
                    "purpose": "Introduce the campaign problem and point of view",
                },
                {
                    "name": "Waitlist conversion sequence",
                    "channel": "Email",
                    "format": "Three-email sequence",
                    "purpose": "Convert campaign interest into qualified signups",
                },
                {
                    "name": "Landing-page hero section",
                    "channel": "Landing Page",
                    "format": "Headline, subhead, and CTA",
                    "purpose": "Turn campaign traffic into a clear next step",
                },
            ],
            "success_metrics": [
                "Qualified waitlist signups",
                "Landing-page conversion rate",
                "Content-to-waitlist conversion rate",
            ],
            "assumptions": [
                "The product has a functioning waitlist destination",
                "The team can provide one proof point or founder example per week",
            ],
            "execution_notes": [
                "Keep calls to action consistent across channels",
                "Review results weekly and refine messages without changing the core promise",
                f"Write primary campaign materials in {output_language} for {target_market} buyers",
            ],
            "market_adaptation": {
                "target_market": target_market,
                "language_strategy": (
                    f"Use concise {output_language} copy with concrete outcomes, practical proof, "
                    "and no literal translation of founder jargon."
                ),
                "positioning_recommendations": [
                    "Lead with the cost of doing campaign work manually",
                    "Show a before-and-after workflow instead of broad AI claims",
                    "Make privacy and model choice visible for cost-sensitive small teams",
                ],
                "localization_notes": [
                    "Use direct benefit-led headlines for English-speaking buyers",
                    "Translate product value, not Chinese startup phrasing, when adapting copy",
                    "Use proof points that match the target market's buying expectations",
                ],
                "cultural_risks": [
                    "Avoid exaggerated automation promises before integrations exist",
                    "Avoid implying external platform publishing is already supported",
                ],
                "suggested_phrases": [
                    "Build your first campaign package before your next standup",
                    "Choose local, Qwen, or GPT based on cost, privacy, and copy quality",
                    "Turn a product idea into editable channel-ready marketing assets",
                ],
            },
            "draft_assets": MockLLMClient._build_draft_assets(
                product_name,
                target_market,
                output_language,
                core_message,
                selected_channels,
            ),
        }

    @staticmethod
    def _selected_channels(request: Dict[str, Any]) -> List[str]:
        channels = request.get("selected_channels") or [
            "LinkedIn",
            "Email",
            "Landing Page",
            "X / Twitter",
        ]
        return [str(channel) for channel in channels if str(channel).strip()]

    @staticmethod
    def _build_channel_plans(
        selected_channels: List[str],
        core_message: str,
        campaign_duration: str,
    ) -> List[Dict[str, Any]]:
        plans = {
            "linkedin": {
                "channel_name": "LinkedIn",
                "role_in_campaign": "Build category awareness and founder credibility",
                "content_types": ["Founder posts", "Problem-solution carousels"],
                "key_messages": [core_message],
                "cadence": f"Three posts per week for {campaign_duration}",
                "success_metrics": ["Qualified profile visits", "Waitlist conversions"],
            },
            "email": {
                "channel_name": "Email",
                "role_in_campaign": "Convert interested prospects into waitlist signups",
                "content_types": ["Launch sequence", "Use-case proof email"],
                "key_messages": ["A practical campaign system for lean teams"],
                "cadence": "One email per week plus launch-day email",
                "success_metrics": ["Click-through rate", "Waitlist conversion rate"],
            },
            "landing page": {
                "channel_name": "Landing Page",
                "role_in_campaign": "Turn campaign traffic into a clear conversion path",
                "content_types": ["Hero section", "Proof block", "CTA module"],
                "key_messages": ["Create the first campaign package without a full marketing team"],
                "cadence": "Publish before the first social push",
                "success_metrics": ["Visitor-to-signup conversion", "CTA click rate"],
            },
            "x / twitter": {
                "channel_name": "X / Twitter",
                "role_in_campaign": "Test sharp founder-facing hooks quickly",
                "content_types": ["Launch thread", "Short proof posts"],
                "key_messages": ["Move from idea to editable assets in one focused sprint"],
                "cadence": "Two short posts and one thread per week",
                "success_metrics": ["Profile visits", "Thread engagement", "Waitlist clicks"],
            },
        }
        result = []
        for channel in selected_channels:
            key = channel.strip().lower()
            result.append(plans.get(key, plans["linkedin"]) | {"channel_name": channel})
        return result or [plans["linkedin"]]

    @staticmethod
    def _build_draft_assets(
        product_name: str,
        target_market: str,
        output_language: str,
        core_message: str,
        selected_channels: List[str],
    ) -> List[Dict[str, Any]]:
        assets = [
            {
                "asset_type": "Social post",
                "channel": "LinkedIn",
                "title": f"Founder narrative for {product_name}",
                "content": (
                    f"Most lean teams do not need another blank content calendar. They need a "
                    f"clear way to turn product context into campaign-ready work. {product_name} "
                    f"helps small teams move from brief to plan to first-draft assets without "
                    f"waiting for a full marketing function.\n\n{core_message}"
                ),
                "call_to_action": "Join the waitlist to build your first campaign sprint.",
                "notes": ["Keep the tone founder-led and practical", "Add one concrete proof point before posting"],
            },
            {
                "asset_type": "Email sequence",
                "channel": "Email",
                "title": f"Three-email waitlist sequence for {target_market}",
                "content": (
                    "Email 1: Name the campaign planning bottleneck and introduce the new workflow.\n"
                    "Email 2: Show how model choice changes cost, privacy, and copy quality.\n"
                    "Email 3: Invite the reader to generate one campaign package and compare outputs."
                ),
                "call_to_action": "Generate a campaign package this week.",
                "notes": [f"Write in {output_language}", "Keep each email under 180 words"],
            },
            {
                "asset_type": "Landing page hero",
                "channel": "Landing Page",
                "title": "Hero section",
                "content": (
                    "Headline: Build your first cross-border campaign package in one focused session.\n"
                    "Subhead: Enter your product, market, and goal, then generate an editable plan, "
                    "channel assets, and localization notes with local, Qwen, or GPT models."
                ),
                "call_to_action": "Create my campaign package",
                "notes": ["Use this as the first above-the-fold test", "Pair with a short product screenshot"],
            },
            {
                "asset_type": "Launch thread",
                "channel": "X / Twitter",
                "title": "Problem-solution thread",
                "content": (
                    "1/ Small teams often know the product, but not the campaign structure.\n"
                    "2/ The hard part is turning scattered context into channel-ready work.\n"
                    "3/ ReelMatrix creates the strategy, first drafts, and market notes in one workflow.\n"
                    "4/ Start with the plan, edit the assets, export the campaign package."
                ),
                "call_to_action": "Try the campaign studio with your next product idea.",
                "notes": ["Swap in a real founder pain point", "Use one metric if available"],
            },
        ]
        selected = {channel.strip().lower() for channel in selected_channels}
        matched = [asset for asset in assets if asset["channel"].lower() in selected]
        return matched or assets[:3]
