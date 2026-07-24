from dataclasses import dataclass
from types import ModuleType

_runtime_mod: ModuleType


def get_shared_parser_source() -> str | None: ...


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    field: str
    code: str
    message: str


class PayloadValidationError(Exception):
    issues: tuple[ValidationIssue, ...]


def parse_case_payload(raw_json: str | bytes) -> object: ...
