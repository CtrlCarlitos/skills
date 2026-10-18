# Git hooks: evaluated, not adopted by default

Per the issue: compare a plain verification command, native Git hooks, and the `pre-commit` framework, and choose the smallest justified solution after checking what the repository actually has -- not a default choice made in advance.

## What this repository actually has

Checked at implementation time: no `.git/hooks/*` beyond Git's own samples, no `.pre-commit-config.yaml`, no `pre-commit` listed in any `requirements.txt`. The baseline is **no hooks, no hook framework**.

## Decision

**Default: no hooks.** The smallest justified solution for a repo with zero existing hook infrastructure is not to introduce one -- `deliver`'s pre-push gate (Section 6 of the issue; `scripts/validation_contract.py`) already enforces the same local-validation contract a `pre-push` hook would, as an explicit step the skill itself runs before pushing. Adding a hook on top would duplicate that enforcement without adding a new guarantee, since `deliver` is already the thing invoking the check -- a hook only matters as a backstop against *forgetting* to invoke it, and `deliver`'s whole purpose is to not forget.

**Not the `pre-commit` framework.** It's a new dependency and a new config file for a repository that has never used it, to do something a same-language script (`validation_contract.py`, already Python, already in this repo) does directly. Per the issue's own framing, don't require a new task-runner framework when existing tooling covers it.

**Native Git hooks: documented as an available, opt-in extension, not built here.** A human (not `deliver` itself) who wants a backstop against running `git push` manually and bypassing the skill can install a `pre-push` hook that calls the same `scripts/validation_contract.py` entry point. Building, testing (including native Windows/PowerShell), and packaging an installable/removable version of that hook -- worktree-compatible, not overwriting unrelated hooks, no silent global git config changes -- is deferred to #23, so the decision gets recorded now without it blocking this skill.

## What `deliver` does instead

`deliver`'s own pre-push step *is* the enforcement point: Section 6 of `SKILL.md` says to build and run the contract before every CI-triggering push, required-push-blocking on a required failure. This happens inside the skill's own flow, not via an external hook Git invokes automatically -- which also means it works identically whether or not the human running `deliver` ever sets up a hook, and whether their host supports Git hooks at all.
