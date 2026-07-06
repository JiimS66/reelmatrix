"""The structured product of the strategy advisor — a one-page strategy a marketer can
SEE and EDIT. The advisor restates its understanding, then OFFERS choices (audience
candidates, positioning angles) for the human to pick/edit rather than a form to fill.

Every offer carries a CONFIDENCE ("guess" until the human confirms it), and `assumptions`
makes the guesses explicit — so the loop never stalls on missing info: it fills a sensible
default, flags it, and lets the human correct it on the next turn."""

from typing import List, Literal

from pydantic import Field

from core.schemas.campaign import NonEmptyStr, StrictSchema

Confidence = Literal["guess", "likely", "confirmed"]


class AudienceCandidate(StrictSchema):
    name: NonEmptyStr
    why: NonEmptyStr  # why they're a strong target
    pain: NonEmptyStr  # the core pain, in their terms
    confidence: Confidence = "guess"  # "this is my guess" until the human confirms


class PositioningAngle(StrictSchema):
    angle: NonEmptyStr
    rationale: NonEmptyStr
    confidence: Confidence = "guess"


class StrategyDraft(StrictSchema):
    understanding: NonEmptyStr  # the advisor restating what it heard (the "tidy-up" start)
    audience_candidates: List[AudienceCandidate] = Field(min_length=1)
    positioning_angles: List[PositioningAngle] = Field(min_length=1)
    content_pillars: List[NonEmptyStr] = Field(min_length=1)
    channels: List[NonEmptyStr]
    measure: NonEmptyStr  # how to tell it's working, in plain language
    assumptions: List[str] = Field(default_factory=list)  # guesses it filled — "correct me"
    next_questions: List[NonEmptyStr]  # what the advisor wants to ask next
