"""Phase 8 — long-to-short atomization: rank candidate clips from a transcript with a
0–100 virality score + a reason + the hook sentence (Opus Clip / SamurAI framework).
Mock heuristic now (hook / number / brevity / power-words); Whisper + an LLM ranker swap
in behind the same interface. Always surfaces the REASON — the score is imperfect, so a
human picks (public tests show ~40% of auto-clips get discarded).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

_POWER = ("how", "why", "secret", "mistake", "never", "stop", "best", "fastest", "proof")


@dataclass
class Clip:
    hook_sentence: str
    clip_score: int
    reason: str
    start: int
    end: int


def _score(sentence: str) -> tuple[int, str]:
    low = sentence.lower()
    score = 40
    reasons: list[str] = []
    if "?" in sentence:
        score += 20
        reasons.append("opens a curiosity loop")
    if any(ch.isdigit() for ch in sentence) or "%" in sentence:
        score += 15
        reasons.append("has a concrete number")
    wc = len(sentence.split())
    if wc <= 14:
        score += 15
        reasons.append("tight enough to land")
    elif wc > 30:
        score -= 10
        reasons.append("too long for a short")
    if any(w in low for w in _POWER):
        score += 15
        reasons.append("strong hook word")
    return max(0, min(100, score)), ", ".join(reasons) or "baseline interest"


class ClipProvider(ABC):
    @abstractmethod
    def rank(self, transcript: str) -> list[Clip]:
        """Ranked candidate clips (best-first), each with a score + reason + hook."""


class MockClipProvider(ClipProvider):
    def rank(self, transcript: str) -> list[Clip]:
        sentences = [
            s.strip()
            for s in (transcript or "").replace("\n", " ").split(".")
            if s.strip()
        ]
        clips: list[Clip] = []
        for i, sent in enumerate(sentences):
            score, reason = _score(sent)
            clips.append(
                Clip(hook_sentence=sent[:90], clip_score=score, reason=reason, start=i, end=i + 1)
            )
        clips.sort(key=lambda c: -c.clip_score)
        return clips[:5]


def create_clip_provider(name: str = "mock") -> ClipProvider:
    return MockClipProvider()
