#!/usr/bin/env bash
# Regression test for sync-vendor.sh's tree-comparison step.
#
# `diff -r --strip-trailing-cr` (the old implementation) only runs on GNU
# diffutils; stock macOS ships BSD diff, which rejects --strip-trailing-cr
# outright, so the maintainer-only `--check` path never ran on a Mac. The
# replacement, `git diff --no-index --ignore-cr-at-eol`, is the same `git`
# binary on every platform sync-vendor.sh already requires.
#
# This test exercises the comparison directly, without network access or
# the upstream clone, by building two local trees. It does not require any
# Python test framework; run it with: bash scripts/tests/test_sync_vendor.sh
set -euo pipefail

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/a/sub" "$work/b/sub"
printf 'line one\nline two\n' > "$work/a/sub/file.txt"
printf 'line one\r\nline two\r\n' > "$work/b/sub/file.txt"

if ! git diff --no-index --ignore-cr-at-eol "$work/a" "$work/b" >/dev/null; then
    echo "FAIL: a CRLF-only difference should be treated as identical" >&2
    exit 1
fi
echo "PASS: CRLF-only difference ignored"

printf 'line one\nline TWO CHANGED\n' > "$work/b/sub/file.txt"

if git diff --no-index --ignore-cr-at-eol "$work/a" "$work/b" >/dev/null; then
    echo "FAIL: a real content difference should be detected" >&2
    exit 1
fi
echo "PASS: real content difference detected"

# --- a cleanup failure must not fail a passing --check ------------------------
# 2026-11-13: sync-vendor.sh's EXIT-trap `rm -rf "$tmp"` raced a still-running
# git process inside the cloned .git/objects ("Directory not empty") and a
# PASSING --check exited 1, turning a green comparison into a red CI step.
# Simulated deterministically here: a stub git (no network, no real clone)
# rebuilds from a fixture and leaves an unreadable directory inside the temp
# tree so the trap's rm fails on purpose. (On filesystems where chmod 000 is a
# no-op, e.g. NTFS without the POSIX layer, the rm succeeds and this case
# passes vacuously - still correct, just not exercising the race.)
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
real_git="$(command -v git)"
stub="$work/bin"
mkdir -p "$stub"
cat >"$stub/git" <<'STUB'
#!/usr/bin/env bash
if [ "${1:-}" = clone ]; then
    mkdir -p "${!#}"
    exit 0
fi
if [ "${1:-}" = -C ]; then
    dir="$2"; shift 2
    if [ "${1:-}" = sparse-checkout ]; then
        printf '%s' "$3" >"$dir/.stub-path"
        exit 0
    fi
    if [ "${1:-}" = checkout ]; then
        path="$(cat "$dir/.stub-path")"
        mkdir -p "$dir/$path"
        cp -r "$VENDOR_FIXTURE/." "$dir/$path/"
        # the race: an unreadable directory inside the temp tree
        mkdir -p "$dir/.git/objects/race"
        touch "$dir/.git/objects/race/loose"
        chmod 000 "$dir/.git/objects/race"
        exit 0
    fi
fi
# exec, not `command git`: PATH still points here, and command git would
# resolve straight back to this stub (infinite recursion).
exec "$REAL_GIT" "$@"
STUB
chmod +x "$stub/git"

root="$work/root"
mkdir -p "$root/scripts" "$root/vendor/fixture-skill/patches" \
    "$root/skills/fixture-skill" "$work/fixture"
cp "$repo_root/scripts/sync-vendor.sh" "$root/scripts/"
cat >"$root/vendor/fixture-skill/UPSTREAM" <<'EOF'
repo=example/upstream
path=skills/thing
commit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
date=2026-01-01
EOF
printf 'skill body\n' >"$work/fixture/SKILL.md"
printf 'skill body\n' >"$root/skills/fixture-skill/SKILL.md"

set +e
out="$(PATH="$stub:$PATH" REAL_GIT="$real_git" VENDOR_FIXTURE="$work/fixture" \
    bash "$root/scripts/sync-vendor.sh" fixture-skill --check 2>&1)"
rc=$?
set -e
case "$out" in
    *PASS:*) ;;
    *) echo "FAIL: the stubbed --check should report PASS (got: $out)" >&2; exit 1 ;;
esac
if [ "$rc" -ne 0 ]; then
    echo "FAIL: a cleanup failure must not change --check's exit code (got $rc)" >&2
    exit 1
fi
echo "PASS: cleanup failure does not fail --check"
chmod 700 "$work/root" 2>/dev/null || true
