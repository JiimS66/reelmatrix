import json
from typing import Any, Dict, Type

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
        core_message = str(ideation.get("core_message", "Create measurable marketing momentum."))
        return {
            "campaign_name": f"{product_name} Lean Growth Launch",
            "campaign_objective": marketing_goal,
            "target_audience": target_audience,
            "core_message": core_message,
            "channels": [
                {
                    "channel_name": "LinkedIn",
                    "role_in_campaign": "Build category awareness and founder credibility",
                    "content_types": ["Founder posts", "Problem-solution carousels"],
                    "key_messages": [core_message],
                    "cadence": "Three posts per week for four weeks",
                    "success_metrics": ["Qualified profile visits", "Waitlist conversions"],
                },
                {
                    "channel_name": "Email",
                    "role_in_campaign": "Convert interested prospects into waitlist signups",
                    "content_types": ["Launch sequence", "Use-case proof email"],
                    "key_messages": ["A practical campaign system for lean teams"],
                    "cadence": "One email per week plus launch-day email",
                    "success_metrics": ["Click-through rate", "Waitlist conversion rate"],
                },
            ],
            "content_pillars": [
                "The cost of fragmented campaign work",
                "Practical AI workflows for lean marketing teams",
                "Evidence of measurable campaign progress",
            ],
            "timeline": [
                {
                    "phase_name": "Foundation",
                    "timing": "Week 1",
                    "objective": "Establish the problem and campaign promise",
                    "key_activities": ["Publish category narrative", "Launch waitlist landing message"],
                },
                {
                    "phase_name": "Activation",
                    "timing": "Weeks 2-4",
                    "objective": "Drive qualified prospects to the waitlist",
                    "key_activities": ["Publish proof-led content", "Run the email launch sequence"],
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
            ],
        }
