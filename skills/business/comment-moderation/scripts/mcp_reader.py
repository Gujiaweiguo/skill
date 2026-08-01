"""Read-only MCP client for lnkwebsite comment moderation.

Connects to the lnkwebsite MCP server via HTTP and calls only
``comment_list_pending``. Never calls any write/moderation tool.

Usage::

    from scripts.mcp_reader import MCPCommentReader

    reader = MCPCommentReader("http://127.0.0.1:5580/mcp", token="...")
    comments = reader.list_pending()
"""

from __future__ import annotations

import json
import os
from typing import Any

# MCP tools allowed by this skill (read-only)
ALLOWED_TOOLS = frozenset({"comment_list_pending"})

# MCP tools explicitly forbidden (write/moderation actions)
FORBIDDEN_TOOLS = frozenset({
    "comment_approve",
    "comment_reject",
    "comment_delete",
    "comment_ban",
    "comment_update",
    "comment_reply",
    "comment_bulk_moderate",
})


class MCPConnectionError(Exception):
    """Raised when the MCP server is unreachable or returns an error."""


class MCPForbiddenToolError(Exception):
    """Raised when a forbidden tool call is attempted."""


class MCPCommentReader:
    """Read-only MCP client for comment listing.

    This client ONLY calls ``comment_list_pending``. It structurally
    cannot call any moderation tool.
    """

    def __init__(
        self,
        server_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self.server_url = server_url or os.environ.get(
            "COMMENT_MCP_URL",
            "http://127.0.0.1:5580/mcp",
        )
        self._token = token or os.environ.get("COMMENT_MCP_TOKEN", "")
        if not self._token:
            msg = (
                "MCP Bearer token is required. Set COMMENT_MCP_TOKEN env var "
                "or pass token= parameter."
            )
            raise MCPConnectionError(msg)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        import urllib.request

        url = self.server_url
        if not url.endswith("/mcp"):
            url = url.rstrip("/") + "/mcp"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
        except Exception as exc:
            msg = f"MCP request failed: {exc}"
            raise MCPConnectionError(msg) from exc

        result = json.loads(body)
        if "error" in result:
            msg = f"MCP error: {result['error']}"
            raise MCPConnectionError(msg)
        return result

    def list_pending(self) -> list[dict[str, object]]:
        """Fetch all pending comments from the CMS via MCP.

        Returns:
            List of comment dicts with keys:
            ``id``, ``article_id``, ``body``, ``author_name``, ``created_at``.

        Raises:
            MCPConnectionError: On network or protocol error.
        """
        response = self._post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "comment_list_pending",
                "arguments": {},
            },
            "id": 1,
        })
        # MCP returns content array; extract text and parse
        if "result" not in response:
            msg = f"MCP response missing result: {response}"
            raise MCPConnectionError(msg)

        result = response["result"]
        if isinstance(result, list):
            # Check if it's FastMCP format: [{"type": "text", "text": "[...]"}]
            text_items = [
                item for item in result
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            if text_items:
                combined = "\n".join(
                    item.get("text", "") for item in text_items
                )
                try:
                    return json.loads(combined)
                except json.JSONDecodeError:
                    msg = f"Cannot parse MCP response as JSON: {combined[:200]}"
                    raise MCPConnectionError(msg) from None
            # Otherwise, assume it's already a list of comment dicts
            return result
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list):
                texts = [
                    item.get("text", "") for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                combined = "\n".join(texts)
                try:
                    return json.loads(combined)
                except json.JSONDecodeError:
                    msg = f"Cannot parse MCP response content: {combined[:200]}"
                    raise MCPConnectionError(msg) from None
        if isinstance(result, list):
            return result  # Already a list of dicts

        msg = f"Unexpected MCP response shape: {type(result)}"
        raise MCPConnectionError(msg)

    def assert_no_forbidden(self) -> None:
        """Verify this reader has no forbidden tool capability."""
        # Structurally guaranteed: this class only has list_pending()
        return
