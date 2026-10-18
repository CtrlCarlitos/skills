#!/usr/bin/env bash
# Rebuild skills/<name> from its pinned upstream commit plus its patch
# queue (vendor/<name>/UPSTREAM + vendor/<name>/patches/*.patch), or verify
# that the committed tree still equals that rebuild.
#
#   scripts/sync-vendor.sh <name>          # replace skills/<name> with upstream@commit + patches
#   scripts/sync-vendor.sh <name> --check  # exit 1 if skills/<name> drifted from that rebuild
#
# To update from upstream: edit commit= (and date=) in vendor/<name>/UPSTREAM,
# run this script, fix any patch that no longer applies (git apply prints the
# rejected hunk), then commit the new tree, UPSTREAM and the patches together.
# Drop a patch once upstream ships the same fix.
set -euo pipefail

name="${1:?Usage: sync-vendor.sh <name> [--check]}"
shift

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target="$root/skills/$name"
vendor_dir="$root/vendor/$name"
# shellcheck source=/dev/null
. "$vendor_dir/UPSTREAM"   # repo= path= commit= date=

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git clone -q --filter=blob:none --no-checkout "https://github.com/$repo.git" "$tmp/up"
git -C "$tmp/up" sparse-checkout set "$path" >/dev/null
git -C "$tmp/up" checkout -q "$commit"

mkdir -p "$tmp/build/skills"
cp -r "$tmp/up/$path" "$tmp/build/skills/$name"
for patch in "$vendor_dir"/patches/*.patch; do
    [ -e "$patch" ] || continue
    ( cd "$tmp/build" && git apply --whitespace=nowarn "$patch" ) ||
        { printf 'sync-vendor: %s does not apply to %s@%s\n' "$(basename "$patch")" "$repo" "${commit:0:12}" >&2; exit 1; }
done

if [ "${1:-}" = "--check" ]; then
    # git diff --no-index, not `diff -r --strip-trailing-cr`: --strip-trailing-cr
    # is GNU-diffutils-only and stock macOS ships BSD diff, which rejects it
    # outright. git is already a hard dependency of this script (it clones
    # upstream), and behaves identically on every platform.
    if git diff --no-index --ignore-cr-at-eol "$tmp/build/skills/$name" "$target" >/dev/null; then
        printf 'PASS: skills/%s == %s %s@%s + %s patch(es)\n' "$name" "$repo" "$path" "${commit:0:12}" "$(ls "$vendor_dir"/patches/*.patch 2>/dev/null | wc -l | tr -d ' ')"
    else
        printf 'FAIL: skills/%s drifted from the rebuild; run scripts/sync-vendor.sh %s or fix the patches\n' "$name" "$name" >&2
        git diff --no-index --ignore-cr-at-eol "$tmp/build/skills/$name" "$target" >&2 || true
        exit 1
    fi
    exit 0
fi

rm -rf "$target"
cp -r "$tmp/build/skills/$name" "$target"
printf 'synced skills/%s from %s %s@%s with %s patch(es)\n' "$name" "$repo" "$path" "${commit:0:12}" "$(ls "$vendor_dir"/patches/*.patch 2>/dev/null | wc -l | tr -d ' ')"
