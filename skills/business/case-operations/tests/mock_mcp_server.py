"""Minimal mock MCP server for case-operations testing.

Simulates the `cases` MCP module: case_create, case_get, case_list.
Records all calls for post-test verification.

Security:
- case_publish / case_unpublish / case_delete are NOT implemented.
  Any attempt to call them raises MockMCPError.
- case_create always returns status=draft.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


# Tools that must NEVER be called by case-operations
FORBIDDEN_MCP_TOOLS = frozenset({
    "case_publish",
    "case_unpublish",
    "case_delete",
    "case_bulk_import",
})

ALLOWED_MCP_TOOLS = frozenset({
    "case_list",
    "case_get",
    "case_create",
    "case_update",
})


@dataclass
class MockCall:
    """Record of a single MCP call."""
    tool: str
    arguments: dict[str, Any]
    timestamp: float
    result: Any = None


@dataclass
class MockMCPServer:
    """In-process mock of the lnkwebsite cases MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _db: dict[str, dict[str, Any]] = field(default_factory=dict)
    _next_id: int = 1

    def case_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Simulate case_create — always returns draft status."""
        case_id = f"fixture-case-{self._next_id:03d}"
        self._next_id += 1
        record = {
            "id": case_id,
            "status": "draft",
            **payload,
        }
        self._db[case_id] = record
        call = MockCall(
            tool="case_create",
            arguments=payload,
            timestamp=time.time(),
            result={"id": case_id, "status": "draft"},
        )
        self.calls.append(call)
        return {"id": case_id, "status": "draft"}

    def case_get(self, case_id: str) -> dict[str, Any] | None:
        """Simulate case_get."""
        result = self._db.get(case_id)
        self.calls.append(MockCall(
            tool="case_get",
            arguments={"id": case_id},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def case_list(self) -> list[dict[str, Any]]:
        """Simulate case_list."""
        result = list(self._db.values())
        self.calls.append(MockCall(
            tool="case_list",
            arguments={},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def case_update(self, case_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Simulate case_update — only if case is draft."""
        if case_id not in self._db:
            raise MockMCPError(f"case not found: {case_id}")
        if self._db[case_id].get("status") != "draft":
            raise MockMCPError(f"cannot update non-draft case: {case_id}")
        self._db[case_id].update(updates)
        self.calls.append(MockCall(
            tool="case_update",
            arguments={"id": case_id, **updates},
            timestamp=time.time(),
            result=self._db[case_id],
        ))
        return self._db[case_id]

    def call(self, tool: str, **kwargs) -> Any:
        """Generic dispatch — rejects forbidden tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool,
                arguments=kwargs,
                timestamp=time.time(),
                result="BLOCKED",
            ))
            raise MockMCPError(
                f"FORBIDDEN tool called: {tool}. "
                f"case-operations must NEVER call publish/unpublish/delete."
            )
        if tool not in ALLOWED_MCP_TOOLS:
            raise MockMCPError(f"unknown tool: {tool}")
        return getattr(self, tool)(**kwargs)

    def get_call_tools(self) -> list[str]:
        """Return ordered list of all tool names called."""
        return [c.tool for c in self.calls]

    def assert_no_forbidden_calls(self) -> None:
        """Assert no forbidden tool was ever called."""
        bad = [c.tool for c in self.calls if c.tool in FORBIDDEN_MCP_TOOLS]
        if bad:
            raise AssertionError(
                f"Forbidden MCP tools were called: {bad}. "
                f"case-operations must NEVER call publish/unpublish/delete."
            )
