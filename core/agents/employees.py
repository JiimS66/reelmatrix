"""Concrete digital employees.

Thin agents that wrap the typed bot logic under the uniform ``Agent`` interface,
plus the role registry the runner resolves against. The bots keep their typed,
unit-tested signatures; these adapters expose them as interchangeable employees.
"""

import json

from core.agents.base import Agent
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.agents.roles import AUDITOR, COPYWRITER, DESIGNER, IDEATION, PLANNING
from core.llm.base import BaseLLMClient
from core.media.factory import create_media_provider, create_vision_provider
from core.schemas.campaign import (
    AuditVerdict,
    CampaignAsset,
    CampaignGenerationRequest,
    IdeationResult,
    VisualAsset,
)


class IdeationAgent(Agent):
    role = IDEATION

    async def run(self, context: dict) -> dict:
        request = CampaignGenerationRequest.model_validate(context["request"])
        result = await IdeationBot(self._llm_client).run(request)
        return result.model_dump(mode="json")


class PlanningAgent(Agent):
    role = PLANNING

    async def run(self, context: dict) -> dict:
        request = CampaignGenerationRequest.model_validate(context["request"])
        ideation = IdeationResult.model_validate(context["ideation_result"])
        plan = await PlanningBot(self._llm_client).run(request, ideation)
        return plan.model_dump(mode="json")


COPYWRITER_SYSTEM_PROMPT = """
You are a senior marketing copywriter. Render ONE platform-optimized post from the
shared campaign content core, the platform's format spec, and the brand. Speak to the
target audience SEGMENT (segment_profile) — lead with its pain_point, land a value_prop,
preempt an objection, and use the reach_tactics for the angle, so the post is tailored,
not generic. Keep the same core message and only the
approved claims as the other channels — be consistent, and never invent unsourced
performance, funding, customer, or user-count claims. Obey the brand voice, tone rules,
and forbidden words, and the platform's length and structure. If revision_notes lists
problems with a previous draft, fix exactly those issues and change nothing else.
Return only the single asset.
""".strip()


class CopywriterAgent(Agent):
    role = COPYWRITER

    async def run(self, context: dict) -> dict:
        payload = {
            "task": "copywriting",
            "channel": context.get("channel", ""),
            "core_message": context.get("core_message", ""),
            "product_name": context.get("product_name", ""),
            "platform": context.get("platform", {}),
            "brand": context.get("brand", {}),
            "segment": context.get("segment", ""),
            "segment_profile": context.get("segment_profile", ""),
            "pain_point": context.get("pain_point", ""),
            "pain_points": context.get("pain_points", []),
            "value_props": context.get("value_props", []),
            "objections": context.get("objections", []),
            "reach_tactics": context.get("reach_tactics", []),
            "recent_feedback": context.get("recent_feedback", []),
            "revision_notes": context.get("revision_notes", []),
        }
        asset = await self._llm_client.generate_structured(
            system_prompt=COPYWRITER_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_model=CampaignAsset,
        )
        return asset.model_dump(mode="json")


AUDITOR_SYSTEM_PROMPT = """
You are an independent marketing content auditor — a different reviewer than the
writer. Judge ONE rendered post against the shared core message, the approved
(source-backed) claims, and the brand voice/tone rules. Flag only real problems on
these dimensions: brand_tone (off-voice or breaks a tone rule), unsourced_claim (a
performance/funding/customer/user-count claim not in the approved claims),
consistency (drifts from the core message), clarity (confusing or off-task). Approve
when there is nothing material to fix. Be precise and conservative — do not invent
issues. Return the verdict only.
""".strip()


class AuditorAgent(Agent):
    role = AUDITOR

    async def run(self, context: dict) -> dict:
        payload = {
            "task": "audit",
            "channel": context.get("channel", ""),
            "core_message": context.get("core_message", ""),
            "approved_claims": context.get("approved_claims", []),
            "brand": context.get("brand", {}),
            "post": context.get("post", {}),
        }
        verdict = await self._llm_client.generate_structured(
            system_prompt=AUDITOR_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_model=AuditVerdict,
        )
        return verdict.model_dump(mode="json")


DESIGNER_SYSTEM_PROMPT = """
You are a senior brand designer. From the shared campaign core, the channel, and the
brand, produce ONE visual spec: a creative concept, a precise image-generation prompt
(composition, subject, mood, on-brand palette — no stock-photo cliche, no text in the
image unless the channel needs it), and accessible alt text. Stay consistent with the
campaign's core message and the brand. If revision_notes lists problems with a previous
draft (e.g. an off-brand palette), fix exactly those. Return the spec only; the image
itself is rendered separately.
""".strip()


class DesignerAgent(Agent):
    """Produces a per-channel visual: an LLM crafts the creative spec, then the
    brand-aware MediaProvider renders the image and fills ``image_ref``."""

    role = DESIGNER

    async def run(self, context: dict) -> dict:
        # Multimodal input: a VLM reads any human-provided reference media into a
        # structured brief, which both informs the spec and feeds image generation
        # as brand references (IP-Adapter / subject-driven personalization).
        refs = context.get("reference_media") or []
        understood: list[dict] = []
        if refs:
            vision = create_vision_provider(context.get("vision_provider", "mock"))
            for ref in refs:
                reading = await vision.understand(media_ref=ref)
                understood.append(
                    {"ref": ref, "summary": reading.summary, "tags": reading.tags}
                )

        payload = {
            "task": "visual_design",
            "channel": context.get("channel", ""),
            "core_message": context.get("core_message", ""),
            "product_name": context.get("product_name", ""),
            "brand": context.get("brand", {}),
            "segment": context.get("segment", ""),
            "segment_description": context.get("segment_description", ""),
            "pain_point": context.get("pain_point", ""),
            "pain_points": context.get("pain_points", []),
            "reference_briefs": [item["summary"] for item in understood],
            "revision_notes": context.get("revision_notes", []),
        }
        spec = await self._llm_client.generate_structured(
            system_prompt=DESIGNER_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_model=VisualAsset,
        )
        provider = create_media_provider(context.get("media_provider", "mock"))
        image = await provider.generate_image(
            prompt=spec.prompt,
            brand=context.get("brand", {}),
            refs=refs or None,
            aspect_ratio=spec.aspect_ratio,
        )
        result = {**spec.model_dump(mode="json"), "image_ref": image.image_ref}
        if understood:
            result["references"] = understood
        return result


_REGISTRY: dict[str, type[Agent]] = {
    IdeationAgent.role.key: IdeationAgent,
    PlanningAgent.role.key: PlanningAgent,
    CopywriterAgent.role.key: CopywriterAgent,
    AuditorAgent.role.key: AuditorAgent,
    DesignerAgent.role.key: DesignerAgent,
}


def agent_for_role(role_key: str, llm_client: BaseLLMClient) -> Agent:
    agent_cls = _REGISTRY.get(role_key)
    if agent_cls is None:
        raise ValueError(f"No agent registered for role '{role_key}'.")
    return agent_cls(llm_client)
