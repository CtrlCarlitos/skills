#!/usr/bin/env bash
# Regression test for sync-skill-creator.sh's tree-comparison step.
#
# `diff -r --strip-trailing-cr` (the old implementation) only runs on GNU
# diffutils; stock macOS ships BSD diff, which rejects --strip-trailing-cr
# outright, so the maintainer-only `--check` path never ran on a Mac. The
# replacement, `git diff --no-index --ignore-cr-at-eol`, is the same `git`
# binary on every platform `sync-skill-creator.sh` already requires.
#
# This test exercises the comparison directly, without network access or
# the upstream clone, by building two local trees. It does not require any
# Python test framework; run it with: bash scripts/tests/test_sync_skill_creator.sh
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
