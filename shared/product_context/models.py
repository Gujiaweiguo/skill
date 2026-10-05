from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Authority:
    status: str
    path: Path | None
    revision: str | None
    evidence: tuple[str, ...] = ()
    source: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "path": str(self.path) if self.path else None,
            "revision": self.revision,
            "evidence": list(self.evidence),
            "source": self.source,
        }


@dataclass(frozen=True)
class CompanyContext:
    id: str
    base: Path
    config_path: Path
    data: dict[str, Any]

    @property
    def products(self) -> list[dict[str, Any]]:
        value = self.data.get("products", [])
        return value if isinstance(value, list) else []


@dataclass(frozen=True)
class ProductContext:
    company: CompanyContext
    id: str
    name: str
    product_status: str
    layers: dict[str, Path | None]
    authority: dict[str, Authority]
    resolution_status: dict[str, str]
    aliases: tuple[str, ...] = ()
    conflicts: tuple[dict[str, Any], ...] = ()
    repo_revision: str | None = None
    openspec_scopes: tuple[str, ...] = ()

    @property
    def code_root(self) -> Path | None:
        return self.layers["code_root"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "company": {
                "id": self.company.id,
                "base": str(self.company.base),
                "config_path": str(self.company.config_path),
            },
            "product": {
                "id": self.id,
                "name": self.name,
                "product_status": self.product_status,
            },
            "layers": {
                key: str(value) if value else None for key, value in self.layers.items()
            },
            "authority": {key: value.as_dict() for key, value in self.authority.items()},
            "resolution_status": self.resolution_status,
            "conflicts": list(self.conflicts),
            "repo_revision": self.repo_revision,
            "openspec": {
                "scope_count": len(self.openspec_scopes),
                "scopes": list(self.openspec_scopes),
            },
            "openspec_scopes": list(self.openspec_scopes),
        }
