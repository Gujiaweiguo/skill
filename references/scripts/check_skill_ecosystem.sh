#!/usr/bin/env bash
#
# check_skill_ecosystem.sh — Skill ecosystem consistency auditor
#
# Encodes every P0/P1/P2 check from references/skill-审计-2026-07.md so drift
# is caught automatically on every new-skill onboarding or OpenSpec change archive.
#
# Usage:
#   ./references/scripts/check_skill_ecosystem.sh           # full audit
#   ./references/scripts/check_skill_ecosystem.sh --quiet   # only print failures
#   ./references/scripts/check_skill_ecosystem.sh --ci      # exit 1 on any P0/P1 fail (no color)
#
# Exit codes:
#   0 = all checks pass (warnings allowed)
#   1 = at least one P0 or P1 check failed
#
# See references/skill-审计-2026-07.md for the human-readable findings this script encodes.

set -uo pipefail

# Resolve repo root (parent of references/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
SYMLINK_DIR="$REPO_ROOT/.opencode/skills"
GITIGNORE="$REPO_ROOT/.gitignore"

# CLI flags
QUIET=0
CI_MODE=0
[ "${1:-}" = "--quiet" ] && QUIET=1
[ "${1:-}" = "--ci" ] && { CI_MODE=1; QUIET=1; }

# Counters
P0_FAIL=0
P1_FAIL=0
P2_WARN=0
P0_PASS=0
P1_PASS=0

# Color codes (disabled in CI mode)
if [ $CI_MODE -eq 0 ]; then
  RED=$'\033[31m'
  YEL=$'\033[33m'
  GRN=$'\033[32m'
  RST=$'\033[0m'
else
  RED=""; YEL=""; GRN=""; RST=""
fi

print_check() {
  local level="$1" status="$2" msg="$3"
  [ $QUIET -eq 1 ] && [ "$status" = "PASS" ] && return 0
  local prefix=""
  case "$level" in
    P0) prefix="${RED}[P0 FAIL]${RST}" ;;
    P1) prefix="${RED}[P1 FAIL]${RST}" ;;
    WARN) prefix="${YEL}[warn]${RST}" ;;
    PASS) prefix="${GRN}[pass]${RST}" ;;
  esac
  printf '%s %s\n' "$prefix" "$msg"
}

# Complex skills per AGENTS.md §「Knowledge Persistence」tier table
# (multi-module packages — troubleshooting.md is REQUIRED for these)
COMPLEX_SKILLS=(
  "skills/business/product-prd-generator"
  "skills/business/bid-doc-master"
  "skills/docs/doc-generator"
)

echo "=== Skill Ecosystem Audit ==="
echo "Repo: $REPO_ROOT"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# P0-1, P0-2: every skill dir must have corresponding .opencode/skills/<name> symlink
# ─────────────────────────────────────────────────────────────────────────────
echo "--- P0: Symlink completeness ---"
while IFS= read -r skill_md; do
  skill_dir=$(dirname "$skill_md")
  skill_name=$(basename "$skill_dir")
  if [ ! -e "$SYMLINK_DIR/$skill_name" ] && [ ! -L "$SYMLINK_DIR/$skill_name" ]; then
    print_check P0 FAIL "Missing symlink: .opencode/skills/$skill_name (skill exists at ${skill_md#$REPO_ROOT/})"
    P0_FAIL=$((P0_FAIL+1))
  else
    P0_PASS=$((P0_PASS+1))
  fi
done < <(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f | sort)

# ─────────────────────────────────────────────────────────────────────────────
# P0: broken symlinks (target missing)
# ─────────────────────────────────────────────────────────────────────────────
while IFS= read -r link; do
  name=$(basename "$link")
  if [ ! -e "$link" ]; then
    target=$(readlink "$link")
    print_check P0 FAIL "Broken symlink: .opencode/skills/$name -> $target (target does not exist)"
    P0_FAIL=$((P0_FAIL+1))
  fi
done < <(find "$SYMLINK_DIR" -maxdepth 1 -type l)

# ─────────────────────────────────────────────────────────────────────────────
# P0: every symlink should point to a dir containing SKILL.md
# (catches "symlink exists but points to wrong place" cases)
# ─────────────────────────────────────────────────────────────────────────────
while IFS= read -r link; do
  name=$(basename "$link")
  if [ -e "$link" ] && [ ! -f "$link/SKILL.md" ]; then
    print_check P0 FAIL "Symlink target has no SKILL.md: .opencode/skills/$name"
    P0_FAIL=$((P0_FAIL+1))
  fi
done < <(find "$SYMLINK_DIR" -maxdepth 1 -type l)

if [ $P0_FAIL -eq 0 ]; then
  print_check PASS PASS "All P0 checks passed ($P0_PASS skill symlinks verified)"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# P1-1: complex skills must have references/troubleshooting.md
# ─────────────────────────────────────────────────────────────────────────────
echo "--- P1: Complex-skill governance ---"
for cs in "${COMPLEX_SKILLS[@]}"; do
  if [ ! -f "$REPO_ROOT/$cs/references/troubleshooting.md" ]; then
    print_check P1 FAIL "Missing troubleshooting.md: $cs/references/troubleshooting.md (complex skill per AGENTS.md tier table)"
    P1_FAIL=$((P1_FAIL+1))
  else
    P1_PASS=$((P1_PASS+1))
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
# P1-3: root .gitignore must cover skills/**/output/ (glob, not hardcoded)
# ─────────────────────────────────────────────────────────────────────────────
if ! grep -qE '^skills/\*\*/output/' "$GITIGNORE"; then
  print_check P1 FAIL "Root .gitignore missing 'skills/**/output/' glob (per AGENTS.md cross-skill rule)"
  P1_FAIL=$((P1_FAIL+1))
else
  P1_PASS=$((P1_PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# P1-6: every SKILL.md frontmatter must be valid YAML with name + description
# (catches orphaned paragraphs after |- blocks, unquoted : in inline values, etc.)
# ─────────────────────────────────────────────────────────────────────────────
if command -v python3 >/dev/null 2>&1 && python3 -c "import yaml" 2>/dev/null; then
  while IFS= read -r skill_md; do
    skill_name=$(basename "$(dirname "$skill_md")")
    err=$(python3 -c "
import yaml
with open('$skill_md') as f:
    content = f.read()
parts = content.split('---', 2)
if len(parts) < 3:
    print('no-frontmatter')
    exit()
try:
    fm = yaml.safe_load(parts[1])
    if not isinstance(fm, dict):
        print('frontmatter-not-dict')
    elif 'name' not in fm or 'description' not in fm:
        print('missing-name-or-description')
except yaml.YAMLError as e:
    print(str(e).split('\n')[0][:120])
" 2>&1)
    if [ -n "$err" ]; then
      print_check P1 FAIL "Invalid SKILL.md frontmatter ($err): $skill_name"
      P1_FAIL=$((P1_FAIL+1))
    fi
  done < <(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f)
else
  print_check WARN n-a "python3+yaml not available — skipping YAML validity check"
fi

# ─────────────────────────────────────────────────────────────────────────────
# P1-2 (drift detection): every custom skill name should appear in AGENTS.md
# dependency graph section at least once
# ─────────────────────────────────────────────────────────────────────────────
DEP_GRAPH_START=$(grep -n "^### Dependency graph" "$REPO_ROOT/AGENTS.md" | head -1 | cut -d: -f1)
DEP_GRAPH_END=$(grep -n "^### word-master calling pattern" "$REPO_ROOT/AGENTS.md" | head -1 | cut -d: -f1)
if [ -n "$DEP_GRAPH_START" ] && [ -n "$DEP_GRAPH_END" ]; then
  DEP_GRAPH_CONTENT=$(sed -n "${DEP_GRAPH_START},${DEP_GRAPH_END}p" "$REPO_ROOT/AGENTS.md")
  while IFS= read -r skill_md; do
    skill_name=$(basename "$(dirname "$skill_md")")
    if ! echo "$DEP_GRAPH_CONTENT" | grep -qF "$skill_name"; then
      print_check P1 FAIL "Skill not in AGENTS.md dependency graph: $skill_name (section spans lines $DEP_GRAPH_START-$DEP_GRAPH_END)"
      P1_FAIL=$((P1_FAIL+1))
    fi
  done < <(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f)
else
  print_check P1 FAIL "Cannot locate AGENTS.md 'Dependency graph' / 'word-master calling pattern' sections"
  P1_FAIL=$((P1_FAIL+1))
fi

if [ $P1_FAIL -eq 0 ]; then
  print_check PASS PASS "All P1 checks passed"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# P2 (soft warnings): non-blocking style/convention drift
# ─────────────────────────────────────────────────────────────────────────────
echo "--- P2 (warnings, non-blocking) ---"

# P2-1: symlinks should use relative paths (../../skills/...) not absolute
while IFS= read -r link; do
  name=$(basename "$link")
  target=$(readlink "$link")
  if [[ "$target" == /* ]]; then
    print_check WARN n/a "Absolute symlink (convention prefers relative): .opencode/skills/$name -> $target"
    P2_WARN=$((P2_WARN+1))
  fi
done < <(find "$SYMLINK_DIR" -maxdepth 1 -type l)

# P2-2 + P1-4 (description length): SKILL.md description should be > 200 chars
# (proxy for trigger-phrase coverage; peers run 300-600)
# Uses python3+yaml if available (most reliable); otherwise skips this check.
if command -v python3 >/dev/null 2>&1 && python3 -c "import yaml" 2>/dev/null; then
  while IFS= read -r skill_md; do
    skill_name=$(basename "$(dirname "$skill_md")")
    desc=$(python3 -c "
import yaml, sys
with open('$skill_md') as f:
    content = f.read()
parts = content.split('---', 2)
if len(parts) < 3:
    sys.exit(0)
try:
    fm = yaml.safe_load(parts[1])
    d = fm.get('description', '') if isinstance(fm, dict) else ''
    print(d)
except Exception:
    pass
" | tr '\n' ' ' | tr -s ' ')
    desc_len=${#desc}
    if [ "$desc_len" -lt 200 ]; then
      print_check WARN n-a "Short description ($desc_len chars, peer median ~400): $skill_name"
      P2_WARN=$((P2_WARN+1))
    fi
  done < <(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f)
else
  print_check WARN n-a "python3+yaml not available — skipping description-length check"
fi

# P1-5 (complex skill References index): complex skill SKILL.md should have ## References section
for cs in "${COMPLEX_SKILLS[@]}"; do
  skill_name=$(basename "$cs")
  if ! grep -qE "^## References" "$REPO_ROOT/$cs/SKILL.md"; then
    print_check WARN n-a "Complex skill missing '## References' index: $skill_name"
    P2_WARN=$((P2_WARN+1))
  fi
done

# P2-3: git-tracked files in any output/ dir (regression check)
TRACKED_OUTPUT=$(cd "$REPO_ROOT" && git ls-files 'skills/*/output/**' 'skills/*/*/output/**' 'skills/*/*/*/output/**' 2>/dev/null)
if [ -n "$TRACKED_OUTPUT" ]; then
  print_check WARN n-a "Files tracked in output/ dir (should be gitignored):"
  echo "$TRACKED_OUTPUT" | sed 's/^/    /'
  P2_WARN=$((P2_WARN+1))
fi

if [ $P2_WARN -eq 0 ]; then
  print_check PASS PASS "No P2 warnings"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo "=== Summary ==="
echo "P0 failures: $P0_FAIL"
echo "P1 failures: $P1_FAIL"
echo "P2 warnings: $P2_WARN"
echo "P0 passes:   $P0_PASS"
echo "P1 passes:   $P1_PASS"

if [ $P0_FAIL -gt 0 ] || [ $P1_FAIL -gt 0 ]; then
  echo ""
  echo "${RED}RESULT: FAIL${RST} — fix P0/P1 issues above. See references/skill-审计-2026-07.md for context."
  exit 1
fi

if [ $P2_WARN -gt 0 ]; then
  echo ""
  echo "${YEL}RESULT: PASS with warnings${RST} — P0/P1 clean; P2 warnings are non-blocking style drift."
else
  echo ""
  echo "${GRN}RESULT: PASS${RST} — ecosystem fully consistent."
fi
exit 0
