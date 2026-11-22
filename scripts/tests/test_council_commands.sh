#!/usr/bin/env bash
# Runs the shell commands that skills/council/SKILL.md and references/agents.md
# tell a coordinator to type, on whatever system this runs on, with stand-ins
# for the agent CLIs. It answers one question per platform: does the shell the
# skill assumes (bash or zsh; Git Bash on Windows) have these commands, and do
# they behave as the skill says?
#
# It launches no agent. It is a repository test, not part of the skill: the
# skill itself ships no script.
#
# Every check prints PASS or FAIL and the run continues, so one CI run shows
# every gap on that platform. Exit status is the number of failed checks.

set -u

fails=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s -- %s\n' "$1" "$2"; fails=$((fails + 1)); }
have() { command -v "$1" >/dev/null 2>&1; }

printf 'system: %s\n' "$(uname -s 2>/dev/null || echo unknown)"
printf 'shell:  bash %s\n' "${BASH_VERSION:-unknown}"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# --- tools the skill names ---------------------------------------------------

for tool in git env jq mkdir cp rm; do
  if have "$tool"; then pass "tool present: $tool"; else fail "tool present: $tool" "not on PATH"; fi
done

# --- launching: command, timeout, env -u -------------------------------------

# The skill writes `timeout`, and `gtimeout` (Homebrew coreutils) where a
# system such as stock macOS has no `timeout`.
limit=""
if have timeout; then limit=timeout
elif have gtimeout; then limit=gtimeout
fi
if [ -n "$limit" ]; then pass "time-limit command present: $limit"
else fail "time-limit command present" "neither timeout nor gtimeout on PATH"; fi

if [ -n "$limit" ]; then
  command "$limit" -k 1 2 sleep 10
  status=$?
  if [ "$status" -eq 124 ]; then pass "time limit ends a turn with status 124"
  else fail "time limit ends a turn with status 124" "got $status"; fi

  command "$limit" -k 1 1 bash -c 'trap "" TERM; sleep 10'
  status=$?
  if [ "$status" -eq 137 ]; then pass "a member that ignores the first signal is killed with status 137"
  else fail "a member that ignores the first signal is killed with status 137" "got $status"; fi

  # A stand-in for an agent that is a native program rather than a shell
  # script: it must really stop, not just be reported as stopped.
  py="$(command -v python3 || command -v python || true)"
  if [ -n "$py" ]; then
    marker="$work/still-running.txt"
    command "$limit" -k 2 2 "$py" -c "import sys, time; time.sleep(6); open(sys.argv[1], 'w').write('alive')" "$marker" < /dev/null
    status=$?
    sleep 8
    if [ "$status" -eq 124 ] || [ "$status" -eq 137 ]; then
      if [ -e "$marker" ]; then fail "a native program is stopped at the time limit" "status $status but it kept running"
      else pass "a native program is stopped at the time limit (status $status)"; fi
    else
      fail "a native program is stopped at the time limit" "got status $status"
    fi
  else
    fail "a native program is stopped at the time limit" "no python to stand in"
  fi

  seen="$(CLAUDECODE=1 command "$limit" -k 1 5 env -u CLAUDECODE bash -c 'echo "${CLAUDECODE:-unset}"')"
  if [ "$seen" = "unset" ]; then pass "env -u removes CLAUDECODE for the member"
  else fail "env -u removes CLAUDECODE for the member" "member saw '$seen'"; fi
else
  fail "time limit checks" "skipped: no timeout command"
fi

# `command` must be a shell builtin the first word can be; timeout cannot run it.
if [ "$(type -t command)" = "builtin" ]; then pass "command is a shell builtin"
else fail "command is a shell builtin" "type -t says '$(type -t command)'"; fi

if have jq; then
  printf '{"is_error":false,"result":"## Recommendation\\nok"}' > "$work/out.json"
  if [ "$(jq -r .result "$work/out.json" | head -n 1)" = "## Recommendation" ]; then pass "jq -r .result prints the answer"
  else fail "jq -r .result prints the answer" "unexpected output"; fi
fi

# --- a repository with uncommitted work --------------------------------------

repo="$work/repo"
mkdir -p "$repo"
cd "$repo" || exit 99
git init -q
git config user.name "council test"
git config user.email "council-test@example.invalid"
printf 'one\n' > tracked.txt
git add tracked.txt
git commit -q -m base
printf 'two\n' > tracked.txt
printf 'new\n' > new.txt

# Step 1: ignore lines, in the local exclude file only.
exclude="$(git rev-parse --git-path info/exclude)"
mkdir -p "$(dirname "$exclude")"
printf 'agent-to-agent/\n.worktrees/\n' >> "$exclude"
if git check-ignore -q agent-to-agent/x && git check-ignore -q .worktrees/x; then pass "local exclude lines ignore the run and worktree directories"
else fail "local exclude lines ignore the run and worktree directories" "check-ignore did not match"; fi

run="2026-01-01-test"
rundir="$repo/agent-to-agent/$run"
mkdir -p "$rundir/round-1" "$rundir/raw/round-1"

base="$(git rev-parse HEAD)"
before="$(git rev-parse HEAD; git --no-optional-locks status --porcelain; git diff --cached --stat)"

# Step 2: the four snapshot commands, exactly as SKILL.md writes them.
GIT_INDEX_FILE="$rundir/snapshot.index" git read-tree HEAD
GIT_INDEX_FILE="$rundir/snapshot.index" git add -A
tree="$(GIT_INDEX_FILE="$rundir/snapshot.index" git write-tree)"
snap1="$(git commit-tree "$tree" -p HEAD -m "council snapshot $run round 1")"

after="$(git rev-parse HEAD; git --no-optional-locks status --porcelain; git diff --cached --stat)"
if [ "$before" = "$after" ]; then pass "snapshot leaves branch, index and working tree unchanged"
else fail "snapshot leaves branch, index and working tree unchanged" "state differs"; fi

if git ls-tree -r --name-only "$snap1" | grep -qx 'new.txt'; then pass "snapshot includes the untracked file"
else fail "snapshot includes the untracked file" "new.txt missing"; fi

if git ls-tree -r --name-only "$snap1" | grep -q '^agent-to-agent/'; then fail "snapshot leaves the run directory out" "agent-to-agent/ is in the snapshot"
else pass "snapshot leaves the run directory out"; fi

if [ -z "$(git for-each-ref)" ] || [ "$(git for-each-ref | wc -l | tr -d ' ')" = "1" ]; then pass "snapshot creates no ref"
else fail "snapshot creates no ref" "unexpected refs: $(git for-each-ref | tr '\n' ' ')"; fi

# Step 4: a member worktree with its own copy of the brief.
wt="$repo/.worktrees/council/$run/member-a"
if git worktree add -q --detach "$wt" "$snap1"; then pass "detached worktree created at the snapshot"
else fail "detached worktree created at the snapshot" "git worktree add failed"; fi

printf 'Reply with exactly: COUNCIL-OK\n' > "$rundir/brief.md"
mkdir -p "$wt/agent-to-agent"
command cp "$rundir/brief.md" "$wt/agent-to-agent/brief.md"

if [ -z "$(git -C "$wt" status --porcelain)" ]; then pass "the brief copy leaves the member worktree's status clean"
else fail "the brief copy leaves the member worktree's status clean" "$(git -C "$wt" status --porcelain | tr '\n' ' ')"; fi

if (cd "$wt" && [ "$(cat agent-to-agent/brief.md)" = "Reply with exactly: COUNCIL-OK" ]); then pass "member reads the brief at the relative path"
else fail "member reads the brief at the relative path" "content differs"; fi

if [ -n "$(git -C "$wt" diff --stat "$base" "$snap1")" ]; then pass "review diff against the literal base hash is not empty"
else fail "review diff against the literal base hash is not empty" "empty diff"; fi

# Another round: new snapshot, move the worktree, both snapshots still held.
printf 'three\n' > tracked.txt
GIT_INDEX_FILE="$rundir/snapshot.index" git read-tree HEAD
GIT_INDEX_FILE="$rundir/snapshot.index" git add -A
tree2="$(GIT_INDEX_FILE="$rundir/snapshot.index" git write-tree)"
snap2="$(git commit-tree "$tree2" -p HEAD -m "council snapshot $run round 2")"
if git -C "$wt" checkout -q --detach "$snap2"; then pass "member worktree moves to the next snapshot"
else fail "member worktree moves to the next snapshot" "checkout failed"; fi

unreachable="$(git fsck --unreachable 2>/dev/null | grep ' commit ' || true)"
if [ -z "$unreachable" ]; then pass "both ref-less snapshots stay reachable through the worktree"
else fail "both ref-less snapshots stay reachable through the worktree" "$unreachable"; fi

# Closing: remove the brief copy, then the worktree.
command rm "$wt/agent-to-agent/brief.md"
# The empty agent-to-agent/ folder is left in place on purpose: the skill no
# longer runs rmdir, and the worktree removal below must take the folder along.
if [ -z "$(git -C "$wt" status --porcelain)" ] && git worktree remove "$wt"; then
  if [ "$(git worktree list | wc -l | tr -d ' ')" = "1" ]; then pass "closing removes the member worktree"
  else fail "closing removes the member worktree" "worktree still listed"; fi
else
  fail "closing removes the member worktree" "worktree not clean or remove failed"
fi

final="$(git rev-parse HEAD; git --no-optional-locks status --porcelain; git diff --cached --stat)"
expected="$(printf '%s\n M tracked.txt\n?? new.txt' "$base")"
if [ "$final" = "$expected" ]; then pass "after the whole run the operator's checkout holds only the operator's own edits"
else fail "after the whole run the operator's checkout holds only the operator's own edits" "got: $final"; fi

printf '\n%s check(s) failed\n' "$fails"
exit "$fails"
