"""Maintenance revision payload building, parsing, and diff rendering."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, Literal, cast

from scripts.article_payload import (
    JsonValue,
    PayloadValidationError,
    ValidationIssue,
)
from scripts.contracts import payload_sha256, write_json

_SHA256: Final = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FIELDS: Final = (
    "entity_type",
    "entity_id",
    "rationale",
    "base_digest",
    "proposed_fields",
)
_ALLOWED_FIELDS: Final = frozenset((*_REQUIRED_FIELDS, "status"))

SERVER_CONTROLLED_FIELDS: Final = frozenset(
    {"id", "status", "published_at", "created_at", "updated_at"},
)


class MaintenanceEntityType(str, Enum):
    """Entity types supported by the maintenance revision contract."""

    ARTICLE = "article"
    CASE = "case"
    PRODUCT = "product"


@dataclass(frozen=True, slots=True)
class MaintenancePayload:
    """Validated maintenance revision payload."""

    entity_type: MaintenanceEntityType
    entity_id: str
    rationale: str
    base_digest: str
    proposed_fields: dict[str, JsonValue]
    status: Literal["pending-review"] = "pending-review"

    def as_json(self) -> dict[str, JsonValue]:
        """Return the payload as a JSON-compatible mapping."""
        return {
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "rationale": self.rationale,
            "base_digest": self.base_digest,
            "proposed_fields": self.proposed_fields,
            "status": self.status,
        }


def _load_json(raw_json: str | bytes) -> JsonValue:
    try:
        return json.loads(raw_json)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PayloadValidationError(
            (ValidationIssue("$", "json_invalid", str(error)),),
        ) from error


def _required_string(
    values: dict[str, JsonValue],
    field: str,
) -> tuple[str | None, ValidationIssue | None]:
    value = values.get(field)
    if value is None:
        return None, ValidationIssue(field, "missing", "field is required")
    if not isinstance(value, str):
        return None, ValidationIssue(field, "string_type", "value must be a string")
    stripped = value.strip()
    if not stripped:
        return None, ValidationIssue(
            field, "string_too_short", "value must be non-empty",
        )
    return stripped, None


def build_proposed_fields(
    current: dict[str, JsonValue],
    desired: dict[str, JsonValue],
) -> tuple[dict[str, JsonValue], list[str]]:
    """Compare current and desired snapshots into a maintenance proposal.

    Returns the proposed (changed) fields excluding server-controlled
    fields, plus the sorted list of server-controlled fields the caller
    attempted to move (client-side pre-check; the server stays the single
    source of truth).
    """
    proposed: dict[str, JsonValue] = {}
    filtered: set[str] = set()
    for field, value in desired.items():
        if field in SERVER_CONTROLLED_FIELDS:
            if current.get(field) != value:
                filtered.add(field)
            continue
        if current.get(field) != value:
            proposed[field] = value
    return proposed, sorted(filtered)


def _validate_proposed_fields(
    raw: dict[str, JsonValue],
    issues: list[ValidationIssue],
) -> dict[str, JsonValue]:
    value = raw.get("proposed_fields")
    if value is None:
        issues.append(
            ValidationIssue("proposed_fields", "missing", "field is required"),
        )
        return {}
    if not isinstance(value, dict):
        issues.append(
            ValidationIssue(
                "proposed_fields", "object_type", "value must be a JSON object",
            ),
        )
        return {}
    if not value:
        issues.append(
            ValidationIssue(
                "proposed_fields",
                "dict_min_length",
                "at least one changed field is required",
            ),
        )
        return {}
    issues.extend(
        ValidationIssue(
            f"proposed_fields.{field}",
            "server_controlled_field",
            "field is server-controlled and cannot be proposed",
        )
        for field in sorted(SERVER_CONTROLLED_FIELDS.intersection(value))
    )
    return dict(value)


def parse_maintenance_payload(raw_json: str | bytes) -> MaintenancePayload:
    """Parse untrusted JSON bytes into a validated maintenance payload."""
    raw = _load_json(raw_json)
    if not isinstance(raw, dict):
        raise PayloadValidationError(
            (ValidationIssue("$", "json_object_required", "payload must be a JSON object"),),
        )

    issues: list[ValidationIssue] = []
    issues.extend(
        ValidationIssue(field, "extra_forbidden", "unknown field is not permitted")
        for field in sorted(set(raw).difference(_ALLOWED_FIELDS))
    )

    strings: dict[str, str] = {}
    for field in ("entity_id", "rationale", "base_digest"):
        value, issue = _required_string(raw, field)
        if issue is not None:
            issues.append(issue)
        elif value is not None:
            strings[field] = value

    entity_type_value = raw.get("entity_type")
    entity_type: MaintenanceEntityType | None = None
    if entity_type_value is None:
        issues.append(
            ValidationIssue("entity_type", "missing", "field is required"),
        )
    else:
        try:
            entity_type = MaintenanceEntityType(entity_type_value)
        except ValueError:
            issues.append(
                ValidationIssue("entity_type", "enum", "entity type is not supported"),
            )

    base_digest = strings.get("base_digest")
    if base_digest is not None and _SHA256.fullmatch(base_digest) is None:
        issues.append(
            ValidationIssue(
                "base_digest",
                "string_pattern_mismatch",
                "base_digest must be a lowercase SHA-256 hex digest",
            ),
        )

    proposed_fields = _validate_proposed_fields(raw, issues)

    status_value = raw.get("status", "pending-review")
    if status_value != "pending-review":
        issues.append(
            ValidationIssue(
                "status", "literal_error", "status must be pending-review",
            ),
        )

    if issues:
        raise PayloadValidationError(
            tuple(sorted(issues, key=lambda issue: (issue.field, issue.code))),
        )
    return MaintenancePayload(
        entity_type=cast("MaintenanceEntityType", entity_type),
        entity_id=strings["entity_id"],
        rationale=strings["rationale"],
        base_digest=strings["base_digest"],
        proposed_fields=proposed_fields,
    )


def render_diff_document(
    entity_type: str,
    entity_id: str,
    current: dict[str, JsonValue],
    proposed: dict[str, JsonValue],
    rationale: str,
) -> str:
    """Render a human-readable before/after diff for maintenance review."""
    lines: list[str] = [
        "# Maintenance Diff Review",
        "",
        f"- entity: `{entity_type}` / `{entity_id}`",
        f"- rationale: {rationale}",
        "",
        "## Changed fields",
        "",
    ]
    if not proposed:
        lines.append("(no changed fields)")
    for field in sorted(proposed):
        before = current.get(field, "«absent»")
        after = proposed[field]
        lines.extend([
            f"### {field}",
            "",
            "```diff",
        ])
        differ = difflib.unified_diff(
            [f"{json.dumps(before, ensure_ascii=False, sort_keys=True)}\n"],
            [f"{json.dumps(after, ensure_ascii=False, sort_keys=True)}\n"],
            fromfile=f"{field} (current)",
            tofile=f"{field} (proposed)",
        )
        lines.extend(differ)
        lines.extend(["```", ""])
    return "\n".join(lines).rstrip() + "\n"


def _read_snapshot_object(path: Path) -> dict[str, JsonValue]:
    try:
        raw: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{path}: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: snapshot must be a JSON object")
    return raw


def build_parser() -> argparse.ArgumentParser:
    """Build the maintenance proposal command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Build one maintenance revision payload and its diff review document."
        ),
    )
    parser.add_argument("--entity-type", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--desired", type=Path, required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    """Build proposed.json and diff-review.md, validating the proposal."""
    args = build_parser().parse_args()
    try:
        current = _read_snapshot_object(args.current)
        desired = _read_snapshot_object(args.desired)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    try:
        entity_type = MaintenanceEntityType(args.entity_type)
    except ValueError:
        print(f"unsupported entity type: {args.entity_type}", file=sys.stderr)
        return 1

    proposed_fields, filtered_fields = build_proposed_fields(current, desired)
    if not proposed_fields:
        print(
            "no mutable field changes between current and desired",
            file=sys.stderr,
        )
        return 1
    if filtered_fields:
        print(
            "server-controlled fields cannot be proposed: "
            + ", ".join(filtered_fields),
            file=sys.stderr,
        )
        return 1

    base_digest = payload_sha256(args.current)
    payload = MaintenancePayload(
        entity_type=entity_type,
        entity_id=args.entity_id,
        rationale=args.rationale,
        base_digest=base_digest,
        proposed_fields=proposed_fields,
    )
    write_json(args.output_dir / "proposed.json", payload.as_json())
    document = render_diff_document(
        entity_type=entity_type.value,
        entity_id=args.entity_id,
        current=current,
        proposed=proposed_fields,
        rationale=args.rationale,
    )
    (args.output_dir / "diff-review.md").write_text(document, encoding="utf-8")
    print(args.output_dir / "proposed.json")
    print(args.output_dir / "diff-review.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
