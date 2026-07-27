"""Minimal mock MCP server for geo-operations testing.

Simulates the ``geo`` MCP module with read-only tools:
``geo_profile_get``, ``geo_profile_list``.  Records all calls for
post-test verification.

Security:
- ``auto_modify_llms_txt``, ``auto_publish_geo_content``,
  ``auto_submit_search_engine``, ``auto_modify_geo_profile`` are
  NOT implemented.  Any attempt to call them raises
  :class:`MockMCPError`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


FORBIDDEN_MCP_TOOLS = frozenset({
    "auto_modify_llms_txt",
    "auto_publish_geo_content",
    "auto_submit_search_engine",
    "auto_modify_geo_profile",
})

ALLOWED_MCP_TOOLS = frozenset({
    "geo_profile_list",
    "geo_profile_get",
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
    """In-process mock of the lnkwebsite geo MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _db: dict[str, dict[str, object]] = field(default_factory=dict)

    def geo_profile_get(
        self, profile_id: str,
    ) -> dict[str, object] | None:
        """Simulate ``geo_profile_get``."""
        result = self._db.get(profile_id)
        self.calls.append(MockCall(
            tool="geo_profile_get",
            arguments={"profile_id": profile_id},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def geo_profile_list(self) -> list[dict[str, object]]:
        """Simulate ``geo_profile_list``."""
        result = list(self._db.values())
        self.calls.append(MockCall(
            tool="geo_profile_list",
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
                "geo-operations must NEVER call modify/publish/submit."
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
                "geo-operations must NEVER call modify/publish/submit."
            )
            raise AssertionError(msg)
