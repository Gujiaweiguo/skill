from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .errors import ResolutionError
from .models import Authority, CompanyContext, ProductContext

_DOCS_ROOT = Path("/opt/code/docs")
_KNOWN_STATES = {
    "complete", "partial", "unresolved", "not-found", "planned", "prd-only",
    "present-unconfirmed", "inaccessible", "unsupported", "not-applicable",
}

# 治理入口 README「权威指针」表格的键标签（按层区分）。
_ONTOLOGY_LABELS: tuple[str, ...] = (
    "canonical ontology",
    "canonical 能力模型",
    "业务本体",
    "本体（域知识）",
    "canonical 本体",
)
_PRD_LABELS: tuple[str, ...] = (
    "PRD 家族",
    "主 PRD",
    "PRD 双轨",
    "PRD 总纲",
    "canonical PRD",
)
# 指针单元格的「显式缺席」前缀：无 / 未建立 / unresolved。
_ABSENT_PREFIXES: tuple[str, ...] = ("无", "未建立", "unresolved")
# 指针单元格的「家族在本目录」标记。
_DIRECTORY_MARKERS: tuple[str, ...] = ("本目录", "已建立")

_SKIP_WALK_DIRS = {
    ".git", ".hg", ".svn", ".venv", "node_modules", "dist", "build",
    "vendor", "__pycache__",
}
_NESTED_OPENSPEC_MAX_DEPTH = 4


def _scalar(value: str) -> Any:
    value = value.split(" #", 1)[0].strip()
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        return [_scalar(item.strip()) for item in value[1:-1].split(",") if item.strip()]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _load_company_yaml(path: Path) -> dict[str, Any]:
    """Parse the small, stable company.yaml contract without a YAML dependency."""
    data: dict[str, Any] = {}
    products: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_products = False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ResolutionError(f"无法读取 company.yaml: {path}: {exc}") from exc
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if stripped == "products:":
            in_products = True
            continue
        if in_products and indent <= 2 and not stripped.startswith("-"):
            in_products = False
            current = None
        if in_products:
            if stripped.startswith("- "):
                current = {}
                products.append(current)
                remainder = stripped[2:].strip()
                if remainder and ":" in remainder:
                    key, value = remainder.split(":", 1)
                    current[key.strip()] = _scalar(value.strip())
                continue
            if current is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = _scalar(value.strip())
            continue
        if ":" in stripped and indent == 0:
            key, value = stripped.split(":", 1)
            data[key.strip()] = _scalar(value.strip())
    data["products"] = products
    return data


def _company_candidates() -> list[Path]:
    if not _DOCS_ROOT.is_dir():
        return []
    return sorted({path.parent.parent for path in _DOCS_ROOT.glob("*/config/company.yaml") if path.is_file()})


def resolve_company(
    company_id: str | None = None,
    company_base: str | Path | None = None,
    cwd: str | Path | None = None,
    require_explicit: bool = False,
) -> CompanyContext:
    configured = company_base or os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")
    candidates = _company_candidates()
    base: Path | None = Path(configured).expanduser() if configured else None
    if base is not None and not base.is_absolute():
        raise ResolutionError(f"公司基座必须是绝对路径: {base}")
    if company_id:
        matches = [candidate for candidate in candidates if candidate.name.lower() == company_id.lower()]
        if base is not None and base.name.lower() != company_id.lower():
            raise ResolutionError(f"company_id 与 company_base 冲突: {company_id!r}, {base}")
        if base is None:
            if len(matches) != 1:
                raise ResolutionError(f"无法唯一解析公司 {company_id!r}: {[str(p) for p in matches]}")
            base = matches[0]
    if base is None and cwd is not None:
        current = Path(cwd).expanduser().resolve()
        for candidate in candidates:
            if current == candidate or candidate in current.parents:
                base = candidate
                break
    if base is None:
        if require_explicit or len(candidates) != 1:
            raise ResolutionError(
                "无法唯一确定公司（发现 "
                f"{[str(candidate) for candidate in candidates]}）；"
                "请显式提供 company_id/company_base 或设置 COMPANY_BASE（不静默默认任何公司）"
            )
        base = candidates[0]
    config_path = base / "config" / "company.yaml"
    if not config_path.is_file():
        raise ResolutionError(f"公司未注册或缺少 company.yaml: {config_path}")
    data = _load_company_yaml(config_path)
    declared_id = data.get("id")
    if declared_id != base.name:
        raise ResolutionError(f"company.yaml id 与目录名不一致: {declared_id!r} != {base.name!r}")
    return CompanyContext(base.name, base, config_path, data)


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, "not-found"
    except PermissionError:
        return None, "inaccessible"
    except UnicodeDecodeError:
        return None, "inaccessible"
    except OSError:
        return None, "inaccessible"


def _table_cell(line: str, labels: tuple[str, ...]) -> str | None:
    """Return the value cell that follows the key cell containing a label."""
    if "|" not in line:
        return None
    segments = line.split("|")
    for index, segment in enumerate(segments[:-1]):
        if any(label.lower() in segment.lower() for label in labels):
            return segments[index + 1].strip()
    return None


def _pointer_from_cell(cell: str) -> tuple[str, Path | None]:
    """Interpret an authority-pointer table cell.

    Returns ``(mode, entry)``: ``unresolved``（显式声明缺席，如「无（unresolved）」/
    「未建立」）、``file``（反引号或 markdown 链接声明的具体条目）、``directory``
    （「本目录 / 已建立」家族声明，或反引号内容是 ``{...}`` 展开记法）、
    或 ``""``（无声明语义）。
    """
    compact = cell.replace(" ", "")
    if any(compact.startswith(prefix) for prefix in _ABSENT_PREFIXES):
        return "unresolved", None
    backtick = re.search(r"`([^`]+)`", cell)
    if backtick:
        value = backtick.group(1).strip()
        if "{" in value or "}" in value:
            return "directory", None
        return "file", Path(value)
    link = re.search(r"\[[^\]]+\]\(([^)\s]+)\)", cell)
    if link:
        return "file", Path(link.group(1).strip())
    if any(marker in cell for marker in _DIRECTORY_MARKERS):
        return "directory", None
    return "", None


def _declared_authority(text: str, labels: tuple[str, ...]) -> tuple[str, Path | None]:
    """Parse the first declarative authority-pointer row of a governance README."""
    for line in text.splitlines():
        cell = _table_cell(line, labels)
        if cell is None:
            continue
        mode, entry = _pointer_from_cell(cell)
        if mode:
            return mode, entry
    return "", None


def _prd_entry_via_markdown_link(text: str) -> Path | None:
    """Fallback for inverted tables (link in the first column, label in the second).

    例如 lnkcrm prd README「当前产物」表：``| [产品PRD.md](./产品PRD.md) | 主文档：… |``。
    只接受相对且不含上跳的本地链接；存在性由调用方核验。
    """
    for match in re.finditer(r"\[([^\]]+)\]\(([^)\s]+)\)", text):
        label_text, target = match.group(1), match.group(2)
        if "prd" not in (label_text + target).lower():
            continue
        path = Path(target)
        if path.is_absolute() or ".." in path.parts:
            continue
        return path
    return None


def _revision(text: str) -> str | None:
    patterns = (r"\b(?:v\d+(?:\.\d+){0,3})\b", r"source_revision[` :]+([0-9a-f]{7,40})")
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0) if match.lastindex is None else match.group(1)
    return None


def _resolve_entry(root: Path, entry: Path | None) -> Path | None:
    if entry is None:
        return None
    if entry.is_absolute():
        return entry
    return (root / entry).resolve()


def _authority(
    status: str,
    path: Path | None,
    evidence: list[str],
    source: str | None = None,
    revision: str | None = None,
) -> Authority:
    if status not in _KNOWN_STATES:
        status = "unresolved"
    if revision is None and path and path.is_file():
        text, _ = _read_text(path)
        if text:
            revision = _revision(text)
    return Authority(status, path, revision, tuple(evidence), source)


def _git_revision(path: Path) -> str | None:
    if not path.is_dir() or not (path / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = result.stdout.strip()
    return revision or None


def _openspec_scopes(path: Path) -> tuple[str, ...]:
    """List spec-scope names across the root and nested openspec directories.

    Root scopes are plain names; nested ones are prefixed with their relative
    parent (for example ``apps/backend/<scope>``). This is a cheap discovery
    summary: unreadable subtrees are skipped here, and the authoritative
    multi-scope audit stays with ``scan_openspec.py``.
    """
    scopes: list[str] = []

    def collect(openspec_dir: Path, prefix: str) -> None:
        specs = openspec_dir / "specs"
        if not specs.is_dir():
            return
        try:
            names = sorted(item.name for item in specs.iterdir() if item.is_dir())
        except OSError:
            return
        scopes.extend(f"{prefix}{name}" for name in names)

    collect(path / "openspec", "")
    for current, dirnames, _filenames in os.walk(path, onerror=lambda _error: None):
        current_path = Path(current)
        if current_path == path:
            dirnames[:] = [
                d for d in dirnames
                if d not in _SKIP_WALK_DIRS and not d.startswith(".") and d != "openspec"
            ]
            continue
        if len(current_path.relative_to(path).parts) >= _NESTED_OPENSPEC_MAX_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in _SKIP_WALK_DIRS and not d.startswith(".")]
        if "openspec" in dirnames:
            openspec_dir = current_path / "openspec"
            if (openspec_dir / "specs").exists() or (openspec_dir / "changes").exists():
                prefix = f"{current_path.relative_to(path).as_posix()}/"
                collect(openspec_dir, prefix)
                dirnames.remove("openspec")
    return tuple(sorted(scopes))


def _observed_code_candidate(product_id: str) -> Path | None:
    candidate = Path("/opt/code") / product_id
    return candidate if candidate.is_dir() and os.access(candidate, os.R_OK) else None


def _match_product(products: list[dict[str, Any]], raw: str) -> dict[str, Any]:
    needle = raw.strip().lower()
    matches = []
    for item in products:
        values = [str(item.get("id", ""))] + [str(alias) for alias in item.get("aliases", []) or []]
        if any(value.lower() == needle for value in values):
            matches.append(item)
    if not matches:
        slug_matches = [item for item in products if str(item.get("id", "")).lower().replace("_", "-") == needle.replace("_", "-")]
        matches = slug_matches
    if len(matches) != 1:
        raise ResolutionError(f"产品 {raw!r} 未注册或匹配不唯一: {[item.get('id') for item in matches]}")
    return matches[0]


def resolve_product(product_id: str, company_context: CompanyContext) -> ProductContext:
    item = _match_product(company_context.data.get("products", []), product_id)
    pid = str(item["id"])
    root = company_context.base / "30-products" / pid
    index = root / "INDEX.md"
    ontology_root = root / "ontology"
    prd_root = root / "prd"
    index_text, _ = _read_text(index)
    ontology_readme = ontology_root / "README.md"
    prd_readme = prd_root / "README.md"
    ontology_text, ontology_error = _read_text(ontology_readme)
    prd_text, prd_error = _read_text(prd_readme)

    ontology_mode, ontology_value = _declared_authority(ontology_text or "", _ONTOLOGY_LABELS)
    ontology_entry: Path | None = None
    if ontology_mode == "file" and ontology_value is not None:
        if ontology_value.is_absolute():
            ontology_entry = ontology_value
        elif ontology_value.parts and ontology_value.parts[0] == "30-products":
            ontology_entry = company_context.base / ontology_value
        else:
            candidates = [
                (ontology_readme.parent / ontology_value).resolve(),
                root / ontology_value,
            ]
            ontology_entry = next((item for item in candidates if item.exists()), candidates[0])
    elif ontology_mode == "directory":
        ontology_entry = ontology_root
    if ontology_entry is None and ontology_text:
        knowledge_match = re.search(r"(?:`域知识\.md`|\[?域知识\.md\]?)\s*(?:\(([^)]+)\))?", ontology_text)
        if knowledge_match:
            target = knowledge_match.group(1) or "域知识.md"
            ontology_entry = _resolve_entry(ontology_readme.parent, Path(target))
    if ontology_entry is None and "business-ontology.yaml" in (ontology_text or ""):
        ontology_entry = company_context.base / "config" / "ontology" / "business-ontology.yaml"
    if ontology_entry is None and (ontology_root / "ontology.yaml").is_file():
        ontology_entry = ontology_root / "ontology.yaml"

    prd_mode, prd_value = _declared_authority(prd_text or "", _PRD_LABELS)
    prd_entry: Path | None = None
    if prd_mode == "file" and prd_value is not None:
        prd_entry = _resolve_entry(prd_readme.parent, prd_value)
    elif prd_mode == "directory":
        prd_entry = prd_root
    elif prd_mode == "" and prd_text:
        if "PRD 家族" in prd_text or "canonical 家族在位" in prd_text:
            prd_entry = prd_root
        else:
            linked = _prd_entry_via_markdown_link(prd_text)
            if linked is not None and (prd_readme.parent / linked).is_file():
                prd_entry = (prd_readme.parent / linked).resolve()
    configured_code = item.get("code_root")
    code_root = Path(configured_code).expanduser() if configured_code else None
    if code_root and not code_root.is_absolute():
        code_root = (company_context.base / code_root).resolve()

    if "prd-only" in (index_text or "").lower() or "prd-only" in (ontology_text or "").lower():
        ontology_status = "not-applicable"
    elif ontology_mode == "unresolved":
        ontology_status = "unresolved"
    elif ontology_error:
        ontology_status = ontology_error
    elif ontology_entry is None:
        ontology_status = "unresolved" if ontology_root.exists() else "not-found"
    elif ontology_entry.exists():
        ontology_status = "complete"
    else:
        ontology_status = "not-found"
    if prd_mode == "unresolved":
        prd_status = "unresolved"
    elif prd_error and prd_error != "not-found":
        prd_status = "inaccessible"
    elif prd_entry is not None and prd_entry.exists():
        prd_status = "complete"
    elif prd_root.exists():
        prd_status = "partial"
    else:
        prd_status = "not-found"
    observed_code = _observed_code_candidate(pid) if configured_code is None else None
    if configured_code is None:
        code_status = "present-unconfirmed" if observed_code else ("planned" if item.get("prd_ready") is False else "unresolved")
        code_path = observed_code
    elif code_root is not None and not code_root.exists():
        code_status = "not-found"
        code_path = code_root
    elif code_root is not None and not os.access(code_root, os.R_OK):
        code_status = "inaccessible"
        code_path = code_root
    else:
        code_status = "complete"
        code_path = code_root
    product_status = "prd-only" if "prd-only" in (index_text or "").lower() or "prd-only" in (ontology_text or "").lower() else str(item.get("product_status") or ("complete" if item.get("prd_ready") else "partial"))
    adapter_status = str(item.get("adapter_status") or "unsupported")
    code_revision = _git_revision(code_path) if code_path else None
    authorities = {
        "ontology": _authority(ontology_status, ontology_entry, [str(ontology_readme), str(index)]),
        "prd": _authority(
            prd_status,
            prd_entry if prd_entry is not None else (prd_readme if prd_readme.exists() else None),
            [str(prd_readme), str(index)],
        ),
        "code": _authority(
            code_status,
            code_path,
            [str(company_context.config_path), str(index)],
            source="company.yaml" if configured_code else "observed-external-checkout",
            revision=code_revision,
        ),
    }
    return ProductContext(
        company_context,
        pid,
        str(item.get("name", pid)),
        product_status,
        adapter_status,
        {
            "docs_root": root if root.exists() else None,
            "index_path": index if index.exists() else None,
            "ontology_root": ontology_root if ontology_root.exists() else None,
            "ontology_entry": ontology_entry,
            "prd_root": prd_root if prd_root.exists() else None,
            "prd_entry": prd_entry,
            "code_root": code_root,
        },
        authorities,
        {"company": "complete", "product": "complete", "ontology": ontology_status, "prd": prd_status, "code": code_status},
        tuple(str(alias) for alias in item.get("aliases", []) or []),
        (),
        code_revision,
        _openspec_scopes(code_path) if code_path else (),
    )
