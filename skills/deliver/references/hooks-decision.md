# Git hooks: evaluated, not adopted by default

Per the issue: compare a plain verification command, native Git hooks, and the `pre-commit` framework, and choose the smallest justified solution after checking what the repository actually has -- not a default choice made in advance.

## What this repository actually has

Checked at implementation time: no `.git/hooks/*` beyond Git's own samples, no `.pre-commit-config.yaml`, no `pre-commit` listed in any `requirements.txt`. The baseline is **no hooks, no hook framework**.

## Decision

**Default: no hooks.** The smallest justified solution for a repo with zero existing hook infrastructure is not to introduce one -- `deliver`'s pre-push gate (Section 6 of the issue; `scripts/validation_contract.py`) already enforces the same local-validation contract a `pre-push` hook would, as an explicit step the skill itself runs before pushing. Adding a hook on top would duplicate that enforcement without adding a new guarantee, since `deliver` is already the thing invoking the check -- a hook only matters as a backstop against *forgetting* to invoke it, and `deliver`'s whole purpose is to not forget.

**Not the `pre-commit` framework.** It's a new dependency and a new config file for a repository that has never used it, to do something a same-language script (`validation_contract.py`, already Python, already in this repo) does directly. Per the issue's own framing, don't require a new task-runner framework when existing tooling covers it.

**Native Git hooks: now built, as an available, opt-in extension -- not the default.** Per #23, `scripts/hook_runner.py` is a non-interactive CLI over the exact same `parse_ci_steps`/`build_local_validation_contract`/`run_contract` functions Section 6 calls inline, and `scripts/install_hooks.py` installs/removes a `pre-commit` + `pre-push` pair that calls it. Worktree-compatible (hooks live in the one shared hooks directory, resolved via `git rev-parse --git-path hooks`, not duplicated per worktree), never overwrites an unrelated existing hook (every hook this tool writes carries its own marker comment; install refuses if a non-marker file is already there), and never touches `git config` -- no silent global change. The hook script itself is a single POSIX-shell file (`#!/bin/sh`), which Windows handles identically to Linux/macOS since Git for Windows already executes hooks through its own bundled shell via the shebang, the same mechanism as everywhere else -- no separate PowerShell variant was needed.

A real hazard surfaced while building this, worth recording: on a machine where `core.hooksPath` is configured globally (not uncommon -- this is how some security/guardrail tooling installs its own hooks across every repo on a machine), `git rev-parse --git-path hooks` resolves to that *same shared, global* directory for every repository, including a disposable throwaway test fixture. A test that exercised this resolution during a file-write, rather than against an isolated fake, overwrote a real, pre-existing file outside any test's control, with no way to recover its prior contents. Filed as `CtrlCarlitos/agent-guardrails#542` (should an agent's writes to that location be protected) and `CtrlCarlitos/dotfiles#425` (should it be dotfiles-managed, so a recoverable copy exists). The lesson folded directly into `install_hooks.py`'s own test suite: every test that writes a hook file injects a fake path resolution; only one narrow, read-only test exercises the real `git rev-parse` call, specifically to prove worktree-sharing.

## What `deliver` does instead

`deliver`'s own pre-push step *is* the enforcement point: Section 6 of `SKILL.md` says to build and run the contract before every CI-triggering push, required-push-blocking on a required failure. This happens inside the skill's own flow, not via an external hook Git invokes automatically -- which also means it works identically whether or not the human running `deliver` ever sets up a hook, and whether their host supports Git hooks at all.
