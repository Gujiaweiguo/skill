"""Risk assessment engine for comment moderation.

Extracts the shared risk-classification logic used by both the
synthetic test runner and the production triage CLI.

Risk levels: ``low`` / ``medium`` / ``high``.
Suggestions: ``approve`` / ``review`` / ``reject``.

This module NEVER calls any MCP tool, NEVER writes to the CMS,
and NEVER performs any moderation action.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

# ── Term catalogues (shared with validate.py) ───────────────────────

FORBIDDEN_TERMS: Final = (
    "解决方案",
    "数字营销",
    "新零售",
    "新商业",
    "新营销",
    "新消费",
)

_FORBIDDEN_TERM_PATTERN: Final = re.compile(
    "|".join(re.escape(t) for t in FORBIDDEN_TERMS),
)

ABSOLUTE_PHRASES: Final = (
    "最领先",
    "最优秀",
    "最大",
    "最小",
    "最好",
    "最差",
    "最强",
    "最弱",
    "最优",
    "最先进",
    "最具",
    "最完善",
    "最专业",
    "最权威",
    "最丰富",
    "最全面",
    "首个",
    "首家",
    "首届一指",
    "唯一",
    "独家",
    "无与伦比",
    "遥遥领先",
    "行业第一",
    "全国第一",
    "全球第一",
)

_ABSOLUTE_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in ABSOLUTE_PHRASES),
)


# ── Data structures ─────────────────────────────────────────────────

@dataclass
class TriageItem:
    """Risk classification for a single comment."""

    comment_id: int
    article_id: int | None = None
    risk_level: str = "low"
    risk_flags: list[str] = field(default_factory=list)
    moderation_suggestion: str = "approve"
    human_review_required: bool = True
    content_snippet: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict for JSON output."""
        return {
            "comment_id": self.comment_id,
            "article_id": self.article_id,
            "risk_level": self.risk_level,
            "risk_flags": self.risk_flags,
            "moderation_suggestion": self.moderation_suggestion,
            "auto_actions_taken": [],
            "human_review_required": self.human_review_required,
            "content_snippet": self.content_snippet,
        }


# ── Public API ──────────────────────────────────────────────────────

def assess_risk(
    comment_id: int,
    content: str,
    article_id: int | None = None,
) -> TriageItem:
    """Classify a single comment into risk level and suggestion.

    Args:
        comment_id: The comment's CMS ID.
        content: The comment body text.
        article_id: Optional article ID for traceability.

    Returns:
        TriageItem with risk_level, risk_flags, and suggestion.
    """
    risk_flags: list[str] = []
    risk_level = "low"

    # Check for forbidden domain terms → high risk
    found_forbidden = _FORBIDDEN_TERM_PATTERN.search(content)
    if found_forbidden:
        risk_flags.append(f"forbidden_term:{found_forbidden.group()}")
        risk_level = "high"

    # Check for absolute marketing phrases → medium risk (unless already high)
    found_absolute = _ABSOLUTE_PATTERN.search(content)
    if found_absolute:
        risk_flags.append(f"absolute_phrase:{found_absolute.group()}")
        if risk_level != "high":
            risk_level = "medium"

    # Check for URLs → medium risk (unless already high)
    if "http" in content or "https" in content:
        risk_flags.append("contains_url")
        if risk_level == "low":
            risk_level = "medium"

    # Check for repeated characters (spam pattern)
    if _has_repeated_chars(content):
        risk_flags.append("repeated_chars")
        if risk_level == "low":
            risk_level = "medium"

    # Map risk level to suggestion
    suggestion = "approve"
    if risk_level == "high":
        suggestion = "reject"
    elif risk_level == "medium":
        suggestion = "review"

    snippet = content[:200] if len(content) > 200 else content

    return TriageItem(
        comment_id=comment_id,
        article_id=article_id,
        risk_level=risk_level,
        risk_flags=risk_flags,
        moderation_suggestion=suggestion,
        human_review_required=True,
        content_snippet=snippet,
    )


def assess_batch(
    comments: list[dict[str, object]],
) -> list[TriageItem]:
    """Classify a batch of comment dicts.

    Each dict must have ``comment_id``/``id`` and ``content``/``body``.
    Optional: ``article_id``.

    Returns:
        List of TriageItems, same order as input.
    """
    items: list[TriageItem] = []
    for comment in comments:
        cid = _get_int(comment, ("comment_id", "id"))
        aid = _get_int(comment, ("article_id",))
        content = _get_str(comment, ("content", "body"))
        if cid is not None and content is not None:
            items.append(assess_risk(cid, content, aid))
    return items


# ── Helpers ─────────────────────────────────────────────────────────

_REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{4,}")


def _has_repeated_chars(text: str, threshold: int = 5) -> bool:
    """Detect 5+ consecutive identical characters (spam indicator)."""
    return bool(_REPEATED_CHAR_PATTERN.search(text))


def _get_int(d: dict[str, object], keys: tuple[str, ...]) -> int | None:
    """Extract an int from the first matching key."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return None


def _get_str(d: dict[str, object], keys: tuple[str, ...]) -> str | None:
    """Extract a non-empty string from the first matching key."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return None
