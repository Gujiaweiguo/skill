#!/usr/bin/env bash
#
# pre-commit.sh — Git pre-commit hook for skill ecosystem governance
#
# Runs check_skill_ecosystem.sh ONLY when the commit touches skill-related files.
# Skip condition keeps unrelated commits fast.
#
# Install (one-time, not auto-installed because .git/hooks/ is not tracked):
#   ln -sf ../../references/scripts/pre-commit.sh .git/hooks/pre-commit
#
# Or use --no-verify on a commit to bypass:
#   git commit --no-verify -m "..."

set -uo pipefail

# Resolve repo root from the hook execution context
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHECK_SCRIPT="$REPO_ROOT/references/scripts/check_skill_ecosystem.sh"

# Bail out silently if the check script isn't present (e.g., fresh partial clone)
[ ! -x "$CHECK_SCRIPT" ] && exit 0

# Triggers exclude references/scripts/ on purpose: the check scripts don't need to re-run themselves.
if ! git diff --cached --name-only | grep -qE '(^skills/.*SKILL\.md$|^\.opencode/skills/|^AGENTS\.md$|^\.gitignore$)'; then
  exit 0
fi

echo "[pre-commit] commit touches skill files — running check_skill_ecosystem.sh..."

if ! "$CHECK_SCRIPT" --ci; then
  echo ""
  echo "[pre-commit] FAILED — fix P0/P1 issues above before committing."
  echo "[pre-commit] To bypass (not recommended): git commit --no-verify ..."
  exit 1
fi

exit 0
