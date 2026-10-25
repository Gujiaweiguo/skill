"""Minimal mock MCP server for content maintenance testing.

Simulates the maintenance_revision MCP module shipped by lnkwebsite slice 1:
``maintenance_revision_create`` (always ``pending-review``) and
``maintenance_revision_get`` (read-only). Records all calls for
post-test verification.

Security:
- ``maintenance_revision_approve`` / ``maintenance_revision_reject`` /
  ``maintenance_revision_apply`` are NOT implemented and have no MCP
  pathway. Any attempt to call them raises :class:`MockMCPError`.
- ``maintenance_revision_create`` always returns ``status=pending-review``.
- Human review/apply happens in the admin UI (outside this Skill);
  tests drive it via :meth:`simulate_human_review_apply` only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class MockMCPError(Exception):
    """Raised when a forbidden or unknown MCP call is attempted."""


FORBIDDEN_MCP_TOOLS = frozenset({
    "maintenance_revision_approve",
    "maintenance_revision_reject",
    "maintenance_revision_apply",
})

ALLOWED_MCP_TOOLS = frozenset({
    "maintenance_revision_create",
    "maintenance_revision_get",
})

SERVER_CONTROLLED_FIELDS = frozenset({
    "id",
    "status",
    "published_at",
    "created_at",
    "updated_at",
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
    """In-process mock of the maintenance_revision MCP module."""

    calls: list[MockCall] = field(default_factory=list)
    _db: dict[str, dict[str, object]] = field(default_factory=dict)
    _next_id: int = 1

    def maintenance_revision_create(
        self,
        entity_type: str,
        entity_id: str,
        rationale: str,
        proposed_fields: dict[str, object],
        base_digest: str,
    ) -> dict[str, object]:
        """Simulate create -- always pending-review, echoes digests."""
        filtered = sorted(SERVER_CONTROLLED_FIELDS.intersection(proposed_fields))
        revision_id = f"mrev-{self._next_id:03d}"
        self._next_id += 1
        record: dict[str, object] = {
            "id": revision_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "rationale": rationale,
            "proposed_fields": dict(proposed_fields),
            "filtered_fields": filtered,
            "base_digest": base_digest,
            "status": "pending-review",
            "reviewer": None,
            "review_digest": None,
            "pre_snapshot_id": None,
            "post_snapshot_id": None,
        }
        self._db[revision_id] = record
        self.calls.append(MockCall(
            tool="maintenance_revision_create",
            arguments={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "rationale": rationale,
                "proposed_fields": dict(proposed_fields),
                "base_digest": base_digest,
            },
            timestamp=time.time(),
            result={
                "id": revision_id,
                "base_digest": base_digest,
                "proposed_fields": dict(proposed_fields),
                "filtered_fields": filtered,
                "status": "pending-review",
            },
        ))
        return dict(self.calls[-1].result, id=revision_id)  # type: ignore[arg-type]

    def maintenance_revision_get(
        self, revision_id: str,
    ) -> dict[str, object] | None:
        """Simulate read-only get."""
        result = self._db.get(revision_id)
        self.calls.append(MockCall(
            tool="maintenance_revision_get",
            arguments={"id": revision_id},
            timestamp=time.time(),
            result=None if result is None else dict(result),
        ))
        return None if result is None else dict(result)

    def simulate_human_review_apply(
        self,
        revision_id: str,
        reviewer: str = "human-reviewer",
        post_snapshot_id: str = "snap-post-001",
    ) -> None:
        """Test-only helper: admin-UI human approve+apply, outside the Skill."""
        record = self._db[revision_id]
        record["status"] = "applied"
        record["reviewer"] = reviewer
        record["review_digest"] = record["base_digest"]
        record["post_snapshot_id"] = post_snapshot_id

    def call(self, tool: str, **kwargs: object) -> object:
        """Generic dispatch -- rejects forbidden and unknown tools."""
        if tool in FORBIDDEN_MCP_TOOLS:
            self.calls.append(MockCall(
                tool=tool,
                arguments=dict(kwargs),
                timestamp=time.time(),
                result="BLOCKED",
            ))
            msg = (
                f"FORBIDDEN tool called: {tool}. "
                "content-operations must NEVER approve/reject/apply maintenance."
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
                "content-operations must NEVER approve/reject/apply maintenance."
            )
            raise AssertionError(msg)
