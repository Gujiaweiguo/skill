"""Minimal mock MCP server for redirect-audit testing.

Simulates the ``redirects`` MCP module and ``url_check``: read-only
operations only. Records all calls for post-test verification.

Security:
- redirect_create / redirect_update / redirect_enable / redirect_disable
  / redirect_delete are NOT implemented.
- auto_modify_nginx / sitemap_write are NOT implemented.
- Any attempt to call them raises MockMCPError.
- redirect_list and url_check are read-only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


FORBIDDEN_MCP_TOOLS = frozenset({
    "redirect_create",
    "redirect_update",
    "redirect_enable",
    "redirect_disable",
    "redirect_delete",
    "auto_modify_nginx",
    "sitemap_write",
})

ALLOWED_MCP_TOOLS = frozenset({
    "redirect_list",
    "redirect_get",
    "url_check",
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
    """In-process mock of the lnkwebsite redirects MCP module (read-only)."""

    calls: list[MockCall] = field(default_factory=list)
    _db: list[dict[str, object]] = field(default_factory=list)

    def load_redirects(self, redirects: list[dict[str, object]]) -> None:
        """Pre-load redirect data into the mock DB."""
        self._db = list(redirects)

    def redirect_list(self) -> list[dict[str, object]]:
        """Simulate redirect_list (read-only)."""
        result = list(self._db)
        self.calls.append(MockCall(
            tool="redirect_list",
            arguments={},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def redirect_get(self, source_url: str) -> dict[str, object] | None:
        """Simulate redirect_get (read-only)."""
        result: dict[str, object] | None = None
        for entry in self._db:
            if entry.get("source_url") == source_url:
                result = entry
                break
        self.calls.append(MockCall(
            tool="redirect_get",
            arguments={"source_url": source_url},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def url_check(self, url: str) -> dict[str, object]:
        """Simulate url_check via mock curl (read-only)."""
        entry = self.redirect_get(url)
        status_code = entry.get("online_status_code", 404) if entry else 404
        result = {"url": url, "status_code": status_code, "reachable": True}
        self.calls.append(MockCall(
            tool="url_check",
            arguments={"url": url},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def call(self, tool: str, **kwargs: object) -> object:
        """Generic dispatch - rejects forbidden tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool,
                arguments=dict(kwargs),
                timestamp=time.time(),
                result="BLOCKED",
            ))
            msg = (
                f"FORBIDDEN tool called: {tool}. "
                "redirect-audit must NEVER call write tools."
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
                "redirect-audit must NEVER call write tools."
            )
            raise AssertionError(msg)
