#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT))

product_context = importlib.import_module("shared.product_context")
ProductContextError = product_context.ProductContextError
resolve_company = product_context.resolve_company
resolve_product = product_context.resolve_product


def _resolve_all(company) -> tuple[dict[str, Any], bool]:
    """Resolve every product registered in company.yaml; per-product failures
    become explicit error entries instead of aborting the whole batch."""
    products: list[dict[str, Any]] = []
    all_ok = True
    for item in company.products:
        pid = str(item.get("id", "")).strip()
        if not pid:
            products.append({"product_id": None, "status": "unresolved", "error": "company.yaml 产品条目缺少 id"})
            all_ok = False
            continue
        try:
            product = resolve_product(pid, company)
        except ProductContextError as error:
            products.append({"product_id": pid, "status": "unresolved", "error": str(error)})
            all_ok = False
            continue
        products.append({"product_id": pid, "status": "resolved", "context": product.as_dict()})
    payload: dict[str, Any] = {
        "company": {
            "id": company.id,
            "base": str(company.base),
            "config_path": str(company.config_path),
        },
        "products": products,
    }
    return payload, all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve company and product authority context.")
    parser.add_argument("product_id", nargs="?", help="产品 ID（或改用 --all 批量解析全部登记产品）")
    parser.add_argument("--all", action="store_true", help="批量解析 company.yaml 登记的全部产品")
    parser.add_argument("--company-id")
    parser.add_argument("--company-base")
    parser.add_argument("--cwd")
    parser.add_argument("--require-explicit", action="store_true")
    args = parser.parse_args()
    if args.all and args.product_id:
        parser.error("--all 与位置参数 product_id 互斥")
    if not args.all and not args.product_id:
        parser.error("必须提供 product_id，或使用 --all 批量解析")
    try:
        company = resolve_company(
            company_id=args.company_id,
            company_base=args.company_base,
            cwd=args.cwd,
            require_explicit=args.require_explicit,
        )
        if args.all:
            payload, all_ok = _resolve_all(company)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if all_ok else 1
        product = resolve_product(args.product_id, company)
    except ProductContextError as error:
        parser.exit(2, f"context resolution failed: {error}\n")
    print(json.dumps(product.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
