# product_context

`product_context` is the read-only, standard-library resolver shared by cross-repository skills.
It discovers a company from `COMPANY_BASE`/`LANLNK_BASE`, an explicit company id, or a cwd under
`/opt/code/docs/<company>`. When several companies are discovered and none is explicitly selected,
resolution fails loudly — it never falls back to a default company such as lanlnk. It validates
`config/company.yaml`, reads the current company's `products` list, and resolves only that
product's `30-products/<id>/` authority pointers.

```python
from product_context import resolve_company, resolve_product

company = resolve_company(company_id="lanlnk")
product = resolve_product("lnkchat", company)
print(product.as_dict())
```

The package has no third-party dependency and does not write YAML, PRD, ontology, code, or
OpenSpec changes. `company.yaml` is the product registry; this package maintains no second registry.
Missing or non-applicable layers are returned explicitly as `unresolved`, `not-found`, `planned`,
`prd-only`, `inaccessible`, `unsupported`, `partial`, or `not-applicable`.
Governance README pointer cells carry explicit semantics: cells declaring `无（unresolved）` /
`未建立` keep the layer `unresolved` (never downgraded to `partial` just because the layer
directory exists); `本目录 / 已建立` family cells resolve the entry to the layer root; backtick
or markdown-link cells resolve to the declared file (`30-products/...` prefixed pointers resolve
against the company base).
When `company.yaml` leaves `code_root: null` but a readable `/opt/code/<product>` checkout
is observed, the code authority is reported as `present-unconfirmed`; the observed path and
revision are evidence only and `layers.code_root` remains null. A configured code root is
required before a layer can be `complete`.

`ProductContext.as_dict()` also exposes `openspec.scope_count` / `openspec.scopes`: root-level
spec scopes are plain names and scopes of nested openspec directories are prefixed with their
relative parent (for example `apps/backend/<scope>`). This is a discovery summary only; the
authoritative multi-scope audit with `inaccessible` handling stays with openspec-practice's
`scan_openspec.py`.

The resolver does not read or merge `product-registry.yaml`. During migration that file is
adapter metadata only; conflicts with `company.yaml` must be reported by the consuming skill
rather than resolved silently.

`ProductContext.adapter_status` is a migration-period compatibility field only (owner decision
O4, `references/adapter-capability-owner-decision-2026-10-04.md`): the resolver passes
`company.yaml products[].adapter_status` through verbatim and falls back to `unsupported` when
the key is absent — `company.yaml` does not define that key, so every product currently
resolves to `unsupported`, which is not an adapter-capability statement. The authority for
per-skill adapter capability is each consuming skill's private
`references/adapter-capabilities.yaml` (owner decisions O1/O2, Plan B). The resolver never
reads capability files, and capability status never overrides product authority status.
New business logic must not read or branch on `adapter_status`; the O4 step-4 prohibition is
enforced mechanically by `tests/test_adapter_status_migration_gate.py`, which also pins the
authority freeze lines (lnkcrm code `complete` — company.yaml `code_root=/opt/code/lnkcrm`,
reconciled by the ratified O5-lnkcrm-code decision record
`references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md`;
lnkgateway ontology `unresolved` with `ontology_entry=null`, lnkwebsite `prd-only` /
ontology `not-applicable`) and fails on any new programmatic `adapter_status` consumer
outside the audited allowlist. Removing the field requires an independent owner approval
(O4 step 5) plus a same-change update to that gate test.

When a skill uses its own uv environment, add the repository root to the process import path
explicitly at its integration boundary, or invoke a small wrapper/CLI that serializes
`ProductContext.as_dict()`. Do not rely on an implicit global installation or a business skill's venv.
