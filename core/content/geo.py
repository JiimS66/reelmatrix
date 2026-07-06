"""Phase 16 — GEO / Answer Engine Optimization: score an asset on the levers that make it
citable by AI search (ChatGPT / Perplexity / Google AI Overviews). Princeton's GEO study
(KDD 2024) found adding statistics (~+40%), citing sources, and quotation/FAQ structure
most improve citability; keyword stuffing hurts. Emitted as an ADVISORY check group (like
policy) — surfaced in the UI but excluded from the content score + self-correction loop.
Fills the long-empty mcp_servers/seo_geo concept."""

from __future__ import annotations

from collections import Counter

_SOURCE_CUES = ("according to", "source", "study", "report", "research", "data show")


def geo_issues(text: str) -> list[dict]:
    """Citability gaps for AI answer engines, as {rule, severity, message, fix} — all
    advisory (warn), since GEO is an optimization, not a hard gate."""
    t = text or ""
    low = t.lower()
    issues: list[dict] = []
    if not any(c.isdigit() for c in t):
        issues.append({
            "rule": "add_statistic", "severity": "warn",
            "message": "No statistic — a concrete number lifts AI citation (~+40%, GEO research).",
            "fix": "Add a stat or data point.",
        })
    if not any(cue in low for cue in _SOURCE_CUES):
        issues.append({
            "rule": "cite_source", "severity": "warn",
            "message": "No cited source — citations improve AI-engine citability.",
            "fix": "Reference a named source or study.",
        })
    if "?" not in t:
        issues.append({
            "rule": "faq_structure", "severity": "warn",
            "message": "No question/FAQ structure — answer engines favor direct Q&A.",
            "fix": "Pose the audience's question, then answer it directly.",
        })
    long_words = [w for w in low.split() if len(w) > 4]
    if long_words:
        word, n = Counter(long_words).most_common(1)[0]
        if n >= 5:
            issues.append({
                "rule": "keyword_stuffing", "severity": "warn",
                "message": f"'{word}' repeats {n}× — keyword stuffing is penalized by answer engines.",
                "fix": "Vary the language.",
            })
    return issues
