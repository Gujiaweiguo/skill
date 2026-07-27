"""Minimal mock MCP server for product-operations testing.

Simulates the ``products`` MCP module: ``product_create``,
``product_get``, ``product_list``, ``product_update``.  Records all
calls for post-test verification.

Security:
- ``product_publish`` / ``product_unpublish`` / ``product_delete`` are
  NOT implemented.  Any attempt to call them raises
  :class:`MockMCPError`.
- ``product_create`` always returns ``status=draft``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class MockMCPError(Exception):
    """Raised when a forbidden MCP call is attempted."""


FORBIDDEN_MCP_TOOLS = frozenset({
    "product_publish",
    "product_unpublish",
    "product_delete",
    "direct_sql",
    "bulk_import",
})

ALLOWED_MCP_TOOLS = frozenset({
    "product_list",
    "product_get",
    "product_create",
    "product_update",
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
    """In-process mock of the products MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _db: dict[str, dict[str, object]] = field(default_factory=dict)
    _next_id: int = 1

    def product_create(
        self, payload: dict[str, object],
    ) -> dict[str, object]:
        """Simulate ``product_create`` -- always returns draft status."""
        product_id = f"fixture-product-{self._next_id:03d}"
        self._next_id += 1
        record: dict[str, object] = {
            "id": product_id,
            "status": "draft",
            **payload,
        }
        self._db[product_id] = record
        self.calls.append(MockCall(
            tool="product_create",
            arguments=dict(payload),
            timestamp=time.time(),
            result={"id": product_id, "status": "draft"},
        ))
        return {"id": product_id, "status": "draft"}

    def product_get(
        self, product_id: str,
    ) -> dict[str, object] | None:
        """Simulate ``product_get``."""
        result = self._db.get(product_id)
        self.calls.append(MockCall(
            tool="product_get",
            arguments={"id": product_id},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def product_list(self) -> list[dict[str, object]]:
        """Simulate ``product_list``."""
        result = list(self._db.values())
        self.calls.append(MockCall(
            tool="product_list",
            arguments={},
            timestamp=time.time(),
            result=result,
        ))
        return result

    def product_update(
        self, product_id: str, updates: dict[str, object],
    ) -> dict[str, object]:
        """Simulate ``product_update`` -- only if product is draft."""
        if product_id not in self._db:
            msg = f"product not found: {product_id}"
            raise MockMCPError(msg)
        if self._db[product_id].get("status") != "draft":
            msg = f"cannot update non-draft product: {product_id}"
            raise MockMCPError(msg)
        self._db[product_id].update(updates)
        self.calls.append(MockCall(
            tool="product_update",
            arguments={"id": product_id, **updates},
            timestamp=time.time(),
            result=self._db[product_id],
        ))
        return self._db[product_id]

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
                "product-operations must NEVER call publish/unpublish/delete."
            )
            raise MockMCPError(msg)
        if tool not in ALLOWED_MCP_TOOLS:
            msg = f"unknown tool: {tool}"
            raise MockMCPError(msg)
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
                "product-operations must NEVER call publish/unpublish/delete."
            )
            raise AssertionError(msg)
