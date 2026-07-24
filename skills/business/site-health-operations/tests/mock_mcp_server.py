"""Minimal mock MCP server for site-health-operations testing.

Simulates read-only health-check MCP tools: ``endpoint_check`` and
``service_status``.  Records all calls for post-test verification.

Security:
- Forbidden tools (restart_service, modify_nginx, modify_systemd,
  modify_cron, modify_iptables, send_alert) are NOT implemented.
  Any attempt to call them raises :class:`MockMCPError`.
- ``endpoint_check`` returns read-only HTTP status data.
- ``service_status`` returns read-only systemd status data.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Final

FORBIDDEN_MCP_TOOLS: Final = frozenset({
    "restart_service",
    "modify_nginx",
    "modify_systemd",
    "modify_cron",
    "modify_iptables",
    "send_alert",
})

ALLOWED_MCP_TOOLS: Final = frozenset({
    "endpoint_check",
    "service_status",
})


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


@dataclass
class MockCall:
    """Record of a single MCP call."""

    tool: str
    arguments: dict[str, object]
    timestamp: float
    result: object = None


@dataclass
class MockMCPServer:
    """In-process mock of the lnkwebsite health MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _services: dict[str, dict[str, object]] = field(
        default_factory=dict,
    )
    _endpoints: dict[str, dict[str, object]] = field(
        default_factory=dict,
    )

    def endpoint_check(
        self, url: str,
    ) -> dict[str, object]:
        """Simulate ``endpoint_check`` -- read-only HTTP probe."""
        cached = self._endpoints.get(url, {
            "url": url,
            "http_code": 200,
            "response_time_ms": 50,
        })
        self.calls.append(MockCall(
            tool="endpoint_check",
            arguments={"url": url},
            timestamp=time.time(),
            result=cached,
        ))
        return cached

    def service_status(
        self, service_name: str,
    ) -> dict[str, object]:
        """Simulate ``service_status`` -- read-only systemctl."""
        cached = self._services.get(service_name, {
            "name": service_name,
            "status": "active",
            "uptime_hours": 1,
        })
        self.calls.append(MockCall(
            tool="service_status",
            arguments={"service_name": service_name},
            timestamp=time.time(),
            result=cached,
        ))
        return cached

    def call(self, tool: str, **kwargs: object) -> object:
        """Generic dispatch -- rejects forbidden tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool,
                arguments=dict(kwargs),  # type: ignore[arg-type]
                timestamp=time.time(),
                result="BLOCKED",
            ))
            msg = (
                f"FORBIDDEN tool called: {tool}. "
                "site-health-operations must NEVER call "
                "restart/modify tools."
            )
            raise MockMCPError(msg)
        if tool not in ALLOWED_MCP_TOOLS:
            unknown_msg = f"unknown tool: {tool}"
            raise MockMCPError(unknown_msg)
        method = getattr(self, tool)
        return method(**kwargs)

    def get_call_tools(self) -> list[str]:
        """Return ordered list of all tool names called."""
        return [c.tool for c in self.calls]

    def assert_no_forbidden_calls(self) -> None:
        """Assert no forbidden tool was ever called."""
        bad = [
            c.tool for c in self.calls
            if c.tool in FORBIDDEN_MCP_TOOLS
        ]
        if bad:
            msg = (
                f"Forbidden MCP tools were called: {bad}. "
                "site-health-operations must NEVER call "
                "restart/modify tools."
            )
            raise AssertionError(msg)
