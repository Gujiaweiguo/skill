#!/usr/bin/env bash
#
# setup_skill_symlinks.sh — Recreate .opencode/skills/<name> symlinks for every skill
#
# Solves the fresh-clone deployment gap: .opencode/ is gitignored (runtime state),
# so a fresh clone has zero symlinks and check_skill_ecosystem.sh reports 21 P0 failures.
# Run this once after cloning, and again whenever a new skill is added.
#
# Idempotent: skips symlinks that already point to the right place;
#             replaces symlinks that point to the wrong place;
#             leaves broken entries for manual inspection.
#
# Usage:
#   ./references/scripts/setup_skill_symlinks.sh           # create/update all symlinks
#   ./references/scripts/setup_skill_symlinks.sh --dry-run # show what would happen
#
# After running, verify with:
#   ./references/scripts/check_skill_ecosystem.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
SYMLINK_DIR="$REPO_ROOT/.opencode/skills"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

mkdir -p "$SYMLINK_DIR"

# Track expected skill names mapped to their canonical relative symlink targets.
# Example: "pricing-generator:../../skills/business/pricing-generator"
declare -a expected=()
while IFS= read -r skill_md; do
  skill_dir=$(dirname "$skill_md")
  skill_name=$(basename "$skill_dir")
  rel_from_repo="${skill_md#$REPO_ROOT/}"                # skills/business/foo/SKILL.md
  skill_subpath=$(dirname "$rel_from_repo")              # skills/business/foo
  expected+=("$skill_name:../../$skill_subpath")
done < <(find "$SKILLS_DIR" -mindepth 3 -maxdepth 3 -name "SKILL.md" -type f | sort)

created=0
replaced=0
skipped=0
broken=0

for entry in "${expected[@]}"; do
  name="${entry%%:*}"
  target="${entry#*:}"
  link_path="$SYMLINK_DIR/$name"

  if [ -L "$link_path" ]; then
    current=$(readlink "$link_path")
    if [ "$current" = "$target" ] && [ -e "$link_path" ]; then
      skipped=$((skipped+1))
      [ $DRY_RUN -eq 1 ] && echo "SKIP   $name -> $target (already correct)"
      continue
    fi
    if [ ! -e "$link_path" ]; then
      broken=$((broken+1))
      echo "BROKEN $name -> $current (target missing — leaving for manual inspection)"
      continue
    fi
    # Points somewhere else but resolves — replace with the canonical relative target
    [ $DRY_RUN -eq 1 ] && echo "REPLACE $name: $current -> $target" && { replaced=$((replaced+1)); continue; }
    rm "$link_path"
    ln -s "$target" "$link_path"
    replaced=$((replaced+1))
    continue
  fi

  if [ -e "$link_path" ]; then
    # Exists but not a symlink — leave for manual inspection (could be a real dir)
    broken=$((broken+1))
    echo "NONLINK $link_path exists but is not a symlink — leaving for manual inspection"
    continue
  fi

  [ $DRY_RUN -eq 1 ] && echo "CREATE  $name -> $target" && { created=$((created+1)); continue; }
  ln -s "$target" "$link_path"
  created=$((created+1))
done

echo ""
echo "=== Summary ==="
echo "Created:  $created"
echo "Replaced: $replaced"
echo "Skipped:  $skipped (already correct)"
echo "Broken:   $broken (needs manual inspection)"
echo "Total skills processed: ${#expected[@]}"

if [ $broken -gt 0 ]; then
  echo ""
  echo "WARNING: $broken broken/non-link entries left for manual inspection."
  echo "Inspect with: ls -la $SYMLINK_DIR/"
  exit 1
fi

if [ $DRY_RUN -eq 0 ]; then
  echo ""
  echo "Next: run ./references/scripts/check_skill_ecosystem.sh to verify P0/P1/P2 status."
fi
exit 0
