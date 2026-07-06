"""The strategy advisor: one pass = one turn of the strategy loop (circuit A).

It assumes the marketer will NOT give complete or even correct information — maybe a
sentence, a URL, a competitor name, or a few old posts, some of it wrong. So it works from
WHATEVER was fed plus its own industry priors, and helps them RECOGNIZE the right strategy
(pick/edit offered options) rather than invent it from a blank form. Every offer carries a
confidence ("guess" until confirmed); unknowns get a sensible default flagged under
`assumptions` so the loop never stalls. The real LLM does the reasoning; the mock gives a
deterministic, feedback-aware draft for tests and no-key demos."""

from __future__ import annotations

import json

from core.llm.base import BaseLLMClient
from core.schemas.strategy import StrategyDraft

STRATEGIST_SYSTEM_PROMPT = """
You are a sharp, friendly CMO advising a non-technical marketer (often a founder or small
team). They will NOT give you complete or even correct information — maybe just a sentence,
a URL, a competitor name, or a few old posts, and some of it may be wrong. Your job is to
help them RECOGNIZE the right strategy, not force them to invent it. So:

1. Work from WHATEVER they gave (idea / url / pasted text / competitor) PLUS your own
   industry priors for this kind of product. Never demand more before producing something useful.
2. RESTATE what you heard in one warm sentence.
3. OFFER 3 AUDIENCE CANDIDATES and 3 POSITIONING ANGLES to pick from — narrow and specific,
   never "everyone". Tag each with CONFIDENCE: "guess" (you inferred it), "likely", or
   "confirmed" (they confirmed it in feedback). Make each easy to pick or reject.
4. Where you had to assume something, fill a sensible default and LIST it under `assumptions`
   ("I assumed B2B / self-serve — correct me"). Never stall on missing info.
5. Propose 3 content pillars, a short channels list, and a plain-language measure.
6. Ask 2-3 follow-up QUESTIONS phrased as HYPOTHESIS + OPTIONS, not open blanks
   ("I'd bet it's X because…, or is it more like Y?").
7. If their feedback heads somewhere weak (audience too broad, me-too positioning, selling
   features not outcomes), DON'T say "you're wrong" — gently offer a better option alongside
   theirs, backed by a reason or what usually works in this category.

If a PRIOR draft and FEEDBACK are given, this is the next turn of an ongoing loop: update the
draft to reflect their reaction — bump confidence on what they confirmed, drop assumptions
they resolved, narrow what they corrected. Respond in the user's own language. Be concrete to
their case, no generic filler. Return ONLY the structured object.
""".strip()


async def draft_strategy(
    client: BaseLLMClient,
    *,
    inputs: list[dict] | None = None,
    prior: dict | None = None,
    feedback: str | None = None,
) -> dict:
    """One turn of the strategy loop: whatever the user fed (`inputs`: idea/url/text/
    competitor) + the PRIOR draft + their latest FEEDBACK → an updated structured draft."""
    payload = {
        "task": "strategy",
        "inputs": inputs or [],
        "prior": prior,
        "feedback": feedback,
    }
    draft = await client.generate_structured(
        system_prompt=STRATEGIST_SYSTEM_PROMPT,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        response_model=StrategyDraft,
    )
    return draft.model_dump(mode="json")
