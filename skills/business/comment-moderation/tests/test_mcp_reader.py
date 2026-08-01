"""Tests for the MCP reader module (scripts.mcp_reader).

Covers: ALLOWED_TOOLS / FORBIDDEN_TOOLS sets, MCPCommentReader initialization,
token requirement, _post request construction, list_pending response parsing
for various MCP response shapes, and error handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.mcp_reader import (
    ALLOWED_TOOLS,
    FORBIDDEN_TOOLS,
    MCPCommentReader,
    MCPConnectionError,
    MCPForbiddenToolError,
)


class TestToolSets:
    def test_allowed_tools_contains_only_read(self) -> None:
        assert "comment_list_pending" in ALLOWED_TOOLS
        # No write tools in allowed set
        assert not (ALLOWED_TOOLS & FORBIDDEN_TOOLS)

    def test_forbidden_tools_contains_all_write_ops(self) -> None:
        expected = {
            "comment_approve", "comment_reject", "comment_delete",
            "comment_ban", "comment_update", "comment_reply",
            "comment_bulk_moderate",
        }
        assert expected <= FORBIDDEN_TOOLS

    def test_no_overlap(self) -> None:
        assert ALLOWED_TOOLS.isdisjoint(FORBIDDEN_TOOLS)


class TestMCPCommentReaderInit:
    def test_requires_token(self) -> None:
        """Without token, raises MCPConnectionError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(MCPConnectionError, match="Bearer token"):
                MCPCommentReader()

    def test_default_url(self) -> None:
        reader = MCPCommentReader(token="test-token")
        assert "127.0.0.1:5580" in reader.server_url

    def test_custom_url(self) -> None:
        reader = MCPCommentReader(
            server_url="http://example.com:9999/api",
            token="t",
        )
        assert "example.com:9999" in reader.server_url

    def test_env_token(self) -> None:
        with patch.dict("os.environ", {"COMMENT_MCP_TOKEN": "env-token"}):
            reader = MCPCommentReader()
            assert reader._token == "env-token"

    def test_env_url(self) -> None:
        with patch.dict("os.environ", {
            "COMMENT_MCP_TOKEN": "t",
            "COMMENT_MCP_URL": "http://custom:1234/mcp",
        }):
            reader = MCPCommentReader()
            assert reader.server_url == "http://custom:1234/mcp"


class TestListPendingParsing:
    """Test parsing various MCP response shapes."""

    def _make_reader(self) -> MCPCommentReader:
        return MCPCommentReader(server_url="http://localhost/mcp", token="t")

    def test_fastmcp_text_array(self) -> None:
        """FastMCP format: result is list of {type: text, text: json_str}."""
        comments = [{"id": 1, "body": "hello"}]
        mock_response = {
            "result": [
                {"type": "text", "text": json.dumps(comments)},
            ],
        }
        reader = self._make_reader()
        with patch.object(reader, "_post", return_value=mock_response):
            result = reader.list_pending()
            assert result == comments

    def test_result_with_content_key(self) -> None:
        """Alternative format: result.content is a list."""
        comments = [{"id": 2, "body": "world"}]
        mock_response = {
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(comments)},
                ],
            },
        }
        reader = self._make_reader()
        with patch.object(reader, "_post", return_value=mock_response):
            result = reader.list_pending()
            assert result == comments

    def test_result_is_already_list(self) -> None:
        """Direct list format — result is already a list of dicts."""
        comments = [{"id": 3, "body": "direct"}]
        mock_response = {"result": comments}
        reader = self._make_reader()
        with patch.object(reader, "_post", return_value=mock_response):
            result = reader.list_pending()
            assert result == comments

    def test_invalid_json_in_text(self) -> None:
        """When MCP text payload isn't valid JSON, raise MCPConnectionError."""
        mock_response = {
            "result": [
                {"type": "text", "text": "not json"},
            ],
        }
        reader = self._make_reader()
        with patch.object(reader, "_post", return_value=mock_response):
            with pytest.raises(MCPConnectionError, match="Cannot parse"):
                reader.list_pending()

    def test_missing_result_key(self) -> None:
        """When response has no 'result', raise MCPConnectionError."""
        reader = self._make_reader()
        with patch.object(reader, "_post", return_value={"error": "bad"}):
            with pytest.raises(MCPConnectionError, match="missing result"):
                reader.list_pending()

    def test_unexpected_result_shape(self) -> None:
        """When result is a bare string, raise MCPConnectionError."""
        reader = self._make_reader()
        with patch.object(reader, "_post", return_value={"result": "weird"}):
            with pytest.raises(MCPConnectionError, match="Unexpected"):
                reader.list_pending()


class TestPostErrorHandling:
    def test_network_error_raises_connection_error(self) -> None:
        reader = MCPCommentReader(server_url="http://localhost/mcp", token="t")
        with patch(
            "urllib.request.urlopen",
            side_effect=ConnectionError("refused"),
        ):
            with pytest.raises(MCPConnectionError, match="MCP request failed"):
                reader._post({"test": True})

    def test_mcp_error_response_raises(self) -> None:
        reader = MCPCommentReader(server_url="http://localhost/mcp", token="t")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"error": {"code": -32600, "message": "invalid"}},
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(MCPConnectionError, match="MCP error"):
                reader._post({"test": True})


class TestAssertNoForbidden:
    """The assert_no_forbidden method is a no-op — structural guarantee."""

    def test_does_not_raise(self) -> None:
        reader = MCPCommentReader(server_url="http://localhost/mcp", token="t")
        reader.assert_no_forbidden()  # should never raise
