"""Minimal mock MCP server for seo-audit testing.

Simulates read-only MCP tools: ``redirect_list`` and ``url_check``.
Records all calls for post-test verification.

Security:
- Write/modify tools are NOT implemented.
- ``sitemap_write``, ``auto_modify_nginx``, ``auto_submit_sitemap``,
  ``auto_modify_canonical``, ``auto_modify_meta`` are explicitly
  blocked.  Any attempt to call them raises :class:`MockMCPError`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Final

FORBIDDEN_MCP_TOOLS: Final[frozenset[str]] = frozenset({
    "sitemap_write",
    "auto_modify_nginx",
    "auto_submit_sitemap",
    "auto_modify_canonical",
    "auto_modify_meta",
    "robots_write",
    "schema_write",
    "meta_write",
})

ALLOWED_MCP_TOOLS: Final[frozenset[str]] = frozenset({
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
    """In-process mock of read-only MCP tools for SEO audit."""

    calls: list[MockCall] = field(default_factory=list)
    _redirects: list[dict[str, str]] = field(default_factory=list)
    _url_results: dict[str, dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Populate default synthetic data."""
        self._redirects = [
            {
                "source": "https://gzshopex.com",
                "target": "https://www.lnkwebsite.com",
                "status": "301",
            },
            {
                "source": "https://shopex.com",
                "target": "https://www.lnkwebsite.com",
                "status": "301",
            },
        ]
        self._url_results = {
            "https://www.lnkwebsite.com/": {
                "url": "https://www.lnkwebsite.com/",
                "http_status": "200",
                "redirect_chain": [],
            },
            "https://www.lnkwebsite.com/capabilities": {
                "url": "https://www.lnkwebsite.com/capabilities",
                "http_status": "200",
                "redirect_chain": [],
            },
            "https://gzshopex.com": {
                "url": "https://www.lnkwebsite.com/",
                "http_status": "301",
                "redirect_chain": [
                    "https://gzshopex.com",
                    "https://www.lnkwebsite.com/",
                ],
            },
        }

    def redirect_list(self) -> list[dict[str, str]]:
        """Simulate ``redirect_list`` — returns all configured redirects."""
        self.calls.append(MockCall(
            tool="redirect_list",
            arguments={},
            timestamp=time.time(),
            result=list(self._redirects),
        ))
        return list(self._redirects)

    def url_check(self, url: str) -> dict[str, str]:
        """Simulate ``url_check`` — returns HTTP status and redirect chain."""
        result = self._url_results.get(
            url,
            {"url": url, "http_status": "404", "redirect_chain": []},
        )
        self.calls.append(MockCall(
            tool="url_check",
            arguments={"url": url},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def call(self, tool: str, **kwargs: object) -> object:
        """Generic dispatch — rejects forbidden tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool,
                arguments=dict(kwargs),
                timestamp=time.time(),
                result="BLOCKED",
            ))
            msg = (
                f"FORBIDDEN tool called: {tool}. "
                "seo-audit is read-only; write/modify tools are blocked."
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
                "seo-audit is read-only; write/modify tools are blocked."
            )
            raise AssertionError(msg)


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""
