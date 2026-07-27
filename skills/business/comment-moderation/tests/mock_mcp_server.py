"""Minimal mock MCP server for comment-moderation testing.

Simulates the ``comments`` MCP module: ``comment_list``, ``comment_get``.
Records all calls for post-test verification.

Security:
- ``comment_approve`` / ``comment_reject`` / ``comment_delete`` / ``comment_ban``
  are NOT implemented.  Any attempt to call them raises :class:`MockMCPError`.
- Only read-only tools are available.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


FORBIDDEN_MCP_TOOLS = frozenset({
    "comment_approve",
    "comment_reject",
    "comment_delete",
    "comment_ban",
    "comment_update",
    "comment_reply",
    "comment_bulk_moderate",
})

ALLOWED_MCP_TOOLS = frozenset({
    "comment_list",
    "comment_get",
})


@dataclass
class MockCall:
    """Record of a single MCP call."""

    tool: str
    arguments: dict[str, object]
    timestamp: float
    result: object = None


@dataclass
class MockMCPServer:
    """In-process mock of the lnkwebsite comments MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _db: dict[int, dict[str, object]] = field(default_factory=dict)

    def comment_get(self, comment_id: int) -> dict[str, object] | None:
        """Simulate ``comment_get``."""
        result = self._db.get(comment_id)
        self.calls.append(MockCall(
            tool="comment_get",
            arguments={"comment_id": comment_id},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def comment_list(self) -> list[dict[str, object]]:
        """Simulate ``comment_list``."""
        result = list(self._db.values())
        self.calls.append(MockCall(
            tool="comment_list",
            arguments={},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def call(self, tool: str, **kwargs: object) -> object:
        """Generic dispatch -- rejects forbidden tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool,
                arguments=dict(kwargs),
                timestamp=time.time(),
                result="BLOCKED",
            ))
            msg = (
                f"FORBIDDEN tool called: {tool}. "
                "comment-moderation must NEVER call write/moderate actions."
            )
            raise MockMCPError(msg)
        if tool not in ALLOWED_MCP_TOOLS:
            unknown_msg = f"unknown tool: {tool}"
            raise MockMCPError(unknown_msg)
        return getattr(self, tool)(**kwargs)

    def get_call_tools(self) -> list[str]:
        """Return ordered list of all tool names called."""
        return [c.tool for c in self.calls]

    def assert_no_forbidden_calls(self) -> None:
        """Assert no forbidden tool was ever called."""
        bad = [c.tool for c in self.calls if c.tool in FORBIDDEN_MCP_TOOLS]
        if bad:
            msg = (
                f"Forbidden MCP tools were called: {bad}. "
                "comment-moderation must NEVER call write/moderate actions."
            )
            raise AssertionError(msg)
