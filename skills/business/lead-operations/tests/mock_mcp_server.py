"""Mock MCP server for lead-operations testing.

Simulates the ``leads`` MCP module: ``lead_list``, ``lead_get``.
Records all calls.  Write tools are forbidden.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


FORBIDDEN_MCP_TOOLS = frozenset({
    "lead_update", "lead_status_change", "lead_assign",
    "lead_delete", "send_email", "send_sms", "send_im",
})

ALLOWED_MCP_TOOLS = frozenset({
    "lead_list", "lead_get",
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
    """In-process mock of the lnkwebsite leads MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _leads: dict[int, dict[str, object]] = field(default_factory=dict)

    def seed(self, leads: list[dict[str, object]]) -> None:
        """Seed the mock with fixture leads."""
        for lead in leads:
            raw_id = lead.get("id")
            if isinstance(raw_id, int):
                self._leads[raw_id] = dict(lead)

    def lead_list(self) -> list[dict[str, object]]:
        """Simulate ``lead_list``."""
        result = list(self._leads.values())
        self.calls.append(MockCall(
            tool="lead_list", arguments={},
            timestamp=time.time(), result=result,
        ))
        return result

    def lead_get(self, lead_id: int) -> dict[str, object] | None:
        """Simulate ``lead_get``."""
        result = self._leads.get(lead_id)
        self.calls.append(MockCall(
            tool="lead_get", arguments={"id": lead_id},
            timestamp=time.time(), result=result,
        ))
        return result

    def call(self, tool: str, **kwargs: object) -> object:
        """Generic dispatch — rejects forbidden tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool, arguments=dict(kwargs),
                timestamp=time.time(), result="BLOCKED",
            ))
            msg = (
                f"FORBIDDEN tool called: {tool}. "
                "lead-operations is read-only."
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
                f"Forbidden MCP tools called: {bad}. "
                "lead-operations is read-only."
            )
            raise AssertionError(msg)
