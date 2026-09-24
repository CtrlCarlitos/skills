#!/usr/bin/env bash
# Rebuild skills/skill-creator from the pinned upstream commit plus our patch
# queue, or verify that the committed tree still equals that rebuild.
#
#   scripts/sync-skill-creator.sh          # replace skills/skill-creator with upstream@commit + patches
#   scripts/sync-skill-creator.sh --check  # exit 1 if skills/skill-creator drifted from that rebuild
#
# To update from upstream: edit commit= (and date=) in vendor/skill-creator/UPSTREAM,
# run this script, fix any patch that no longer applies (git apply prints the
# rejected hunk), then commit the new tree, UPSTREAM and the patches together.
# Drop a patch once upstream ships the same fix.
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target="$root/skills/skill-creator"
# shellcheck source=/dev/null
. "$root/vendor/skill-creator/UPSTREAM"   # repo= path= commit= date=

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git clone -q --filter=blob:none --no-checkout "https://github.com/$repo.git" "$tmp/up"
git -C "$tmp/up" sparse-checkout set "$path" >/dev/null
git -C "$tmp/up" checkout -q "$commit"

mkdir -p "$tmp/build/skills"
cp -r "$tmp/up/$path" "$tmp/build/skills/skill-creator"
for patch in "$root"/vendor/skill-creator/patches/*.patch; do
    [ -e "$patch" ] || continue
    ( cd "$tmp/build" && git apply --whitespace=nowarn "$patch" ) ||
        { printf 'sync-skill-creator: %s does not apply to %s@%s\n' "$(basename "$patch")" "$repo" "${commit:0:12}" >&2; exit 1; }
done

if [ "${1:-}" = "--check" ]; then
    if diff -r --strip-trailing-cr "$tmp/build/skills/skill-creator" "$target" >/dev/null; then
        printf 'PASS: skills/skill-creator == %s %s@%s + %s patch(es)\n' "$repo" "$path" "${commit:0:12}" "$(ls "$root"/vendor/skill-creator/patches/*.patch 2>/dev/null | wc -l | tr -d ' ')"
    else
        printf 'FAIL: skills/skill-creator drifted from the rebuild; run scripts/sync-skill-creator.sh or fix the patches\n' >&2
        diff -r --strip-trailing-cr "$tmp/build/skills/skill-creator" "$target" >&2 || true
        exit 1
    fi
    exit 0
fi

rm -rf "$target"
cp -r "$tmp/build/skills/skill-creator" "$target"
printf 'synced skills/skill-creator from %s %s@%s with %s patch(es)\n' "$repo" "$path" "${commit:0:12}" "$(ls "$root"/vendor/skill-creator/patches/*.patch 2>/dev/null | wc -l | tr -d ' ')"
