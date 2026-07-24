"""Type stub for content_ops_loader — mirrors content-ops case_payload API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    field: str
    code: str
    message: str


class PayloadValidationError(Exception):
    issues: tuple[ValidationIssue, ...]


def parse_case_payload(raw_json: str | bytes) -> object: ...
