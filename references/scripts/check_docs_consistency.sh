#!/usr/bin/env bash
#
# check_docs_consistency.sh — Cross-skill shared-file consistency auditor
#
# Validates that the "shared files" contract declared in AGENTS.md matches
# what skills actually reference. Catches drift in both directions:
#   - Over-claim: AGENTS.md says skill X reads file Y, but X doesn't reference Y
#   - Under-claim: skill X actually references file Y, but AGENTS.md doesn't list X
#
# Scope: /opt/code/skill + /opt/code/docs (the shared infrastructure skill repo governs).
# Does NOT audit other software repos (mi / langchat / etc.) — those are out of scope
# per the 2026-07-19 user boundary decision.
#
# Usage:
#   ./references/scripts/check_docs_consistency.sh           # full audit
#   ./references/scripts/check_docs_consistency.sh --quiet   # only print failures
#   ./references/scripts/check_docs_consistency.sh --ci      # exit 1 on any FAIL
#
# Exit codes:
#   0 = all checks pass (warnings allowed)
#   1 = at least one existence or reader-claim check failed
#
# See AGENTS.md §「Shared files (update both sides when changing)」 for the human-readable contract.
# When AGENTS.md table changes, update SHARED_FILES below to match.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
LANLNK_BASE="${LANLNK_BASE:-/opt/code/docs/lanlnk}"

QUIET=0
CI_MODE=0
[ "${1:-}" = "--quiet" ] && QUIET=1
[ "${1:-}" = "--ci" ] && { CI_MODE=1; QUIET=1; }

FAIL=0
WARN=0
PASS=0

if [ $CI_MODE -eq 0 ]; then
  RED=$'\033[31m'; YEL=$'\033[33m'; GRN=$'\033[32m'; RST=$'\033[0m'
else
  RED=""; YEL=""; GRN=""; RST=""
fi

print_result() {
  local level="$1" msg="$2"
  [ $QUIET -eq 1 ] && [ "$level" = "PASS" ] && return 0
  local prefix
  case "$level" in
    FAIL) prefix="${RED}[FAIL]${RST}" ;;
    WARN) prefix="${YEL}[warn]${RST}" ;;
    PASS) prefix="${GRN}[pass]${RST}" ;;
  esac
  printf '%s %s\n' "$prefix" "$msg"
}

# Shared files contract — keep in sync with AGENTS.md §「Shared files」table.
# Format: "filepath|declared_readers_comma_sep"
# Declared readers are the skills AGENTS.md claims should reference the file by its basename.
# NOTE: this hardcoded list is the authoritative contract AGENTS.md table must match;
# update both sides together. Any drift flagged by the script indicates one side is stale.
SHARED_FILES=(
  "skills/business/material-importer/references/domain-tags.md|material-importer,product-prd-generator,compound-learning"
  "skills/business/product-prd-generator/references/term-aliases.yaml|product-prd-generator,competitor-product-analyzer"
  "skills/business/product-prd-generator/references/product-governance/source-reference.schema.json|product-prd-generator,material-importer,competitor-product-analyzer"
  "skills/business/product-prd-generator/references/product-governance/layer-reference.schema.json|product-prd-generator,openspec-practice"
  "skills/business/product-prd-generator/references/product-governance/ontology-change-set.schema.json|product-prd-generator,competitor-product-analyzer,openspec-practice"
  "skills/business/product-prd-generator/references/product-governance/reconciliation-record.schema.json|product-prd-generator,openspec-practice"
  "skills/business/product-prd-generator/references/product-governance/implementation-return.schema.json|product-prd-generator,openspec-practice"
  "$LANLNK_BASE/30-products/lnkcre/ontology/domain-knowledge.md|product-prd-generator,competitor-product-analyzer"
  "$LANLNK_BASE/config/ontology/business-ontology.yaml|product-prd-generator,competitor-product-analyzer"
)

echo "=== Docs Cross-Skill Consistency Audit ==="
echo "Repo: $REPO_ROOT"
echo "LANLNK_BASE: $LANLNK_BASE"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check 1: Each declared shared file must exist
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Check 1: Shared file existence ---"
for entry in "${SHARED_FILES[@]}"; do
  path="${entry%%|*}"
  # Resolve relative paths against repo root
  if [[ "$path" != /* ]]; then
    full_path="$REPO_ROOT/$path"
    display="$path"
  else
    full_path="$path"
    display="${path/$LANLNK_BASE/\$LANLNK_BASE}"
  fi
  if [ ! -e "$full_path" ]; then
    print_result FAIL "Missing shared file: $display"
    FAIL=$((FAIL+1))
  else
    PASS=$((PASS+1))
  fi
done
[ $QUIET -eq 0 ] && print_result PASS "Existence check complete"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check 2: Reader-claim drift (over-claim and under-claim)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Check 2: Reader-claim drift ---"

# Build the list of all skill names (for under-claim detection)
declare -a all_skills=()
while IFS= read -r skill_md; do
  all_skills+=("$(basename "$(dirname "$skill_md")")")
done < <(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f)

for entry in "${SHARED_FILES[@]}"; do
  path="${entry%%|*}"
  declared="${entry#*|}"

  # Resolve path
  if [[ "$path" != /* ]]; then
    full_path="$REPO_ROOT/$path"
  else
    full_path="$path"
  fi
  if [ ! -e "$full_path" ]; then
    # Already flagged in Check 1; skip reader analysis
    continue
  fi

  # The basename is what skills actually grep for in their SKILL.md and references/
  fname=$(basename "$path")

  # Find which skills reference this filename
  declare -A actual_readers=()
  for skill_md in $(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f); do
    skill_name=$(basename "$(dirname "$skill_md")")
    skill_dir=$(dirname "$skill_md")
    # Search SKILL.md and references/ for the filename
    if grep -rqF "$fname" "$skill_dir" 2>/dev/null; then
      actual_readers["$skill_name"]=1
    fi
  done

  # Diff declared vs actual
  IFS=',' read -ra declared_arr <<< "$declared"
  declare -A declared_set=()
  for d in "${declared_arr[@]}"; do
    declared_set["$d"]=1
  done

  # Over-claim: declared but not actually referencing
  for d in "${declared_arr[@]}"; do
    if [ -z "${actual_readers[$d]:-}" ]; then
      print_result WARN "Over-claim: AGENTS.md says '$d' reads $fname, but $d doesn't reference it"
      WARN=$((WARN+1))
    fi
  done

  # Under-claim: actually referencing but not declared
  for actual in "${!actual_readers[@]}"; do
    if [ -z "${declared_set[$actual]:-}" ]; then
      print_result WARN "Under-claim: '$actual' references $fname, but AGENTS.md doesn't list it as a reader"
      WARN=$((WARN+1))
    fi
  done
done
[ $QUIET -eq 0 ] && print_result PASS "Reader-claim drift check complete"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check 3: Critical docs subdirectories exist
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Check 3: Critical docs subdirectories ---"
# Lazy-created dirs (created by skills on first run) are WARN, not FAIL.
# COMPANIES.md §3：从 COMPANY_BASE 派生（旧默认 lanlnk/UserGuide 已废弃）。
LAZY_DIRS=("${USERGUIDE_BASE:-$LANLNK_BASE/materials/03-products/user-guides}")
CRITICAL_DIRS=(
  "$LANLNK_BASE/incoming"
  "$LANLNK_BASE/raw"
  "$LANLNK_BASE/materials"
  "$LANLNK_BASE/out/proposals"
  "$LANLNK_BASE/out/bidding"
  "$LANLNK_BASE/config/ontology"
)
for dir in "${CRITICAL_DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    print_result FAIL "Missing critical dir: $dir"
    FAIL=$((FAIL+1))
  else
    PASS=$((PASS+1))
  fi
done
for dir in "${LAZY_DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    print_result WARN "Lazy-created dir not yet present (will be created by skill on first run): $dir"
    WARN=$((WARN+1))
  else
    PASS=$((PASS+1))
  fi
done
[ $QUIET -eq 0 ] && print_result PASS "Critical dirs check complete"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check 4: Product dir registration (docs 30-products/ vs company.yaml products)
# ─────────────────────────────────────────────────────────────────────────────
# 2026-09-26 复利：docs 侧产品 onboarding（新建 30-products/<pid>/）后，skill 侧
# 必须跟进登记——未登记产品的 ontology 解析会静默回落商管 business-ontology
# （lnkcrm 实证）。WARN 而非 FAIL：docs 先行 / skill 跟进是合法节奏，但 drift
# 必须每次审计可见，不靠人工复核发现。
# B2 迁移（2026-10-04）：对账面自 product-registry.yaml 改为 company.yaml products
# （唯一产品台账，COMPANIES.md §3）；registry 已于 2026-10-04 D1 退役删除（迁移审计 §4-B2
# 与 D1 收官注记；执行记录见 references/adapter-capability-owner-decision-b2-execution-2026-10-04.md）。
echo "--- Check 4: Product dir registration ---"
PRODUCTS_DIR="$LANLNK_BASE/30-products"
COMPANY_YAML="$LANLNK_BASE/config/company.yaml"
if [ -d "$PRODUCTS_DIR" ] && [ -f "$COMPANY_YAML" ]; then
  # company.yaml products 为 list 形态（“  - id: <pid>”）。仅对 products: 块对账，
  # 防止其他 section 未来出现同形 list 条目误判；块边界 = 下一个非缩进非注释行
  # （含 # --- products-end --- marker 与 strategy: 等顶层键）。
  PRODUCTS_BLOCK="$(awk '/^products:/{f=1;next} f && /^[^[:space:]#]/{exit} f' "$COMPANY_YAML")"
  if [ -n "$PRODUCTS_BLOCK" ]; then
    for product_dir in "$PRODUCTS_DIR"/*/; do
      [ -d "$product_dir" ] || continue
      pid=$(basename "$product_dir")
      if ! grep -qE "^  - id: ${pid}[[:space:]]*($|#)" <<<"$PRODUCTS_BLOCK"; then
        print_result WARN "Unregistered product dir: 30-products/$pid (company.yaml products 无条目；未登记产品的 ontology 解析会静默回落商管，请跟进注册)"
        WARN=$((WARN+1))
      else
        PASS=$((PASS+1))
      fi
    done
    [ $QUIET -eq 0 ] && print_result PASS "Product registration check complete"
  else
    print_result WARN "Product registration check skipped: no products: section in company.yaml"
    WARN=$((WARN+1))
  fi
else
  print_result WARN "Product registration check skipped: missing $PRODUCTS_DIR or company.yaml"
  WARN=$((WARN+1))
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check 5: Shared files must be git-tracked (fresh-clone view)
# 2026-10-02 复利：磁盘上存在 ≠ fresh clone 后存在。Check 1 只看磁盘视角；
# 本检查按 git 索引（git ls-files）校验，堵「引用已推送、被引用物未提交」
# 的悬空类事故（实证：6c5c5b3 前夜 product-governance 目录 untracked 悬空）。
# 仓内相对路径查 skill 仓索引；$LANLNK_BASE 绝对路径查 docs 仓自身索引。
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Check 5: Shared files tracked (git view) ---"
if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  for entry in "${SHARED_FILES[@]}"; do
    path="${entry%%|*}"
    if [[ "$path" == /* ]]; then
      if git -C "$LANLNK_BASE" rev-parse --git-dir >/dev/null 2>&1; then
        rel_docs="${path#"$LANLNK_BASE"/}"
        if [ -z "$(git -C "$LANLNK_BASE" ls-files -- "$rel_docs")" ]; then
          print_result FAIL "Shared file exists on disk but NOT tracked in docs repo (fresh clone would lose it): $rel_docs"
          FAIL=$((FAIL+1))
        else
          PASS=$((PASS+1))
        fi
      else
        print_result WARN "docs base not inside a git repo — skipping tracked-view: ${path/#$LANLNK_BASE/\$LANLNK_BASE}"
        WARN=$((WARN+1))
      fi
    else
      if [ -z "$(git -C "$REPO_ROOT" ls-files -- "$path")" ]; then
        print_result FAIL "Shared file exists on disk but NOT git-tracked (fresh clone would lose it): $path"
        FAIL=$((FAIL+1))
      else
        PASS=$((PASS+1))
      fi
    fi
  done
  [ $QUIET -eq 0 ] && print_result PASS "Tracked-view check complete"
else
  print_result WARN "Not a git repo — skipping tracked-view check"
  WARN=$((WARN+1))
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo "=== Summary ==="
echo "FAIL:    $FAIL"
echo "WARN:    $WARN"
echo "PASS:    $PASS"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "${RED}RESULT: FAIL${RST} — fix FAIL items above. See AGENTS.md §「Shared files」 for contract."
  exit 1
fi

if [ $WARN -gt 0 ]; then
  echo ""
  echo "${YEL}RESULT: PASS with warnings${RST} — existence OK; reader-claim drift is informational. Update AGENTS.md or skill references to align."
else
  echo ""
  echo "${GRN}RESULT: PASS${RST} — shared files consistent."
fi
exit 0
