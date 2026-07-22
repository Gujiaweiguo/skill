"""Narrow HTTP adapter for lnkwebsite CMS draft creation."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from scripts.contracts import JsonValue

ENDPOINT_ENV: Final = "CONTENT_CMS_DRAFT_ENDPOINT"
TOKEN_ENV: Final = "CONTENT_CMS_TOKEN"
_REQUEST_TIMEOUT_SECONDS: Final = 30


@dataclass(frozen=True, slots=True)
class CmsConfig:
    """Non-secret endpoint and runtime-injected bearer token."""

    endpoint: str
    token: str


class CmsRequestError(Exception):
    """Raised when the configured CMS endpoint cannot complete a request."""


class CmsResponseError(Exception):
    """Raised when the CMS response does not prove draft creation."""


def _validate_config(config: CmsConfig) -> None:
    parsed_endpoint = urllib.parse.urlparse(config.endpoint)
    if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
        message = f"{ENDPOINT_ENV}: must be a configured http(s) endpoint"
        raise CmsRequestError(message)
    if not config.token.strip():
        message = f"{TOKEN_ENV}: must be configured in the environment"
        raise CmsRequestError(message)


def _parse_draft_response(response_body: bytes) -> tuple[str, Literal["draft"]]:
    try:
        raw: JsonValue = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CmsResponseError(str(error)) from error
    if not isinstance(raw, dict):
        message = "response must be a JSON object"
        raise CmsResponseError(message)
    article_id = raw.get("id")
    if isinstance(article_id, bool) or not isinstance(article_id, (int, str)):
        message = "response id must be an integer or string"
        raise CmsResponseError(message)
    if raw.get("status") != "draft":
        message = "response status must be draft"
        raise CmsResponseError(message)
    return str(article_id), "draft"


def create_cms_draft(
    config: CmsConfig,
    request_body: bytes,
) -> tuple[str, Literal["draft"]]:
    """Create one CMS record and return only a confirmed draft result."""
    _validate_config(config)
    request = urllib.request.Request(
        config.endpoint,
        data=request_body,
        headers={
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            response_body = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        raise CmsRequestError(str(error)) from error
    return _parse_draft_response(response_body)
