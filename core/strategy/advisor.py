"""The strategy advisor: a CMO-style guide that turns a fuzzy idea into a structured,
editable marketing strategy. It RESTATES what it heard, then OFFERS audience candidates +
positioning angles for the human to pick/edit/reject — marketers are better at choosing
than at staring at a blank form. The real LLM does the reasoning (this is the one feature
whose only 'data' is an LLM key); the mock gives a deterministic plausible draft for tests
and no-key demos."""

from __future__ import annotations

import json

from core.llm.base import BaseLLMClient
from core.schemas.strategy import StrategyDraft

STRATEGIST_SYSTEM_PROMPT = """
You are a sharp, friendly CMO advising a non-technical marketer (often a founder or small
team) who has a fuzzy idea and needs a clear strategy. DON'T lecture and DON'T demand they
fill in a form. Instead:
1. RESTATE what you heard in one warm sentence, so they feel understood.
2. OFFER 3 distinct AUDIENCE CANDIDATES (name, why they're a strong target, their core pain
   in their own words) — narrow and specific, never "everyone". Make them easy to pick or reject.
3. OFFER 3 distinct POSITIONING ANGLES (a crisp angle + why it works for this audience).
4. Propose 3 CONTENT PILLARS, a short CHANNELS list, and a plain-language MEASURE of success.
5. Ask 2-3 follow-up QUESTIONS that move the thinking forward (challenge vagueness; ask for proof).
Translate any jargon into plain words. Respond in the user's own language. Be concrete and
specific to their idea — no generic filler. Return ONLY the structured object.
""".strip()


async def draft_strategy(
    client: BaseLLMClient, *, idea: str, answers: list[dict] | None = None
) -> dict:
    """One advisor pass: a fuzzy idea (+ any prior answers) → a structured strategy draft."""
    payload = {"task": "strategy", "idea": idea, "answers": answers or []}
    draft = await client.generate_structured(
        system_prompt=STRATEGIST_SYSTEM_PROMPT,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        response_model=StrategyDraft,
    )
    return draft.model_dump(mode="json")
