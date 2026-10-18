# deliver git-hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an installable/removable `pre-commit` + `pre-push` git hook pair for `deliver` that delegates to the exact same `validation_contract.py` the skill already uses inline, closing CtrlCarlitos/skills#23 item 1.

**Architecture:** A new `scripts/hook_runner.py` adds a non-interactive CLI entry point over `validation_contract.py`'s existing functions (no duplication of the parse/build/run logic) -- reads a repo's `.github/workflows/ci.yml`, runs the contract, prints a summary, exits 1 if any required step failed. A new `scripts/install_hooks.py` writes/removes a tiny POSIX-shell hook script (invoked by git on every platform including Windows, via Git for Windows' own shebang-based hook execution -- no `.ps1` variant needed) into the target repo's real hooks directory, resolved via `git rev-parse --git-path hooks` so it works correctly from a worktree.

**Tech Stack:** Python 3 stdlib + the existing `pyyaml` dependency (already in `requirements.txt`).

**Spec:** CtrlCarlitos/skills#23 item 1, and `references/hooks-decision.md`'s existing deferral note.

## Global Constraints

- Never silently overwrites an unrelated existing hook -- a hook file not carrying this tool's own install marker comment blocks install with an error, never a forced overwrite.
- Never changes git config (no `core.hooksPath` edit) -- installs directly into the repo's existing, real hooks directory.
- Worktree-compatible: hooks live in the one shared hooks directory (`git rev-parse --git-path hooks`), not per-worktree, and install/uninstall must work when invoked from inside a worktree.
- The installed hook script itself must be a plain POSIX shell script with a `#!/bin/sh` shebang -- this is what git already knows how to execute identically on Linux, macOS, and Windows (via Git for Windows' bundled shell), so no separate PowerShell variant is needed.
- `hook_runner.py` must reuse `parse_ci_steps`/`build_local_validation_contract`/`run_contract` from `validation_contract.py` unchanged -- no second copy of CI-step-to-command logic.

## Review Focus

- **Uninstall must not remove a hook this tool didn't install.** If a user has their own unrelated `pre-commit` hook, `uninstall` must refuse to touch it (same marker check as install). Tested in Task 2.
- **A required step failing must produce a non-zero exit code; an optional (`continue-on-error`) step failing must not.** This is the entire enforcement value of the hook -- a bug here makes it silently toothless. Tested in Task 1.
- **Install must work identically when invoked from a linked worktree, not just the main checkout** -- the issue names this explicitly. Tested in Task 2.
- **The hook script must locate `hook_runner.py` by an absolute path baked in at install time**, not a relative path that breaks once git's working directory differs from where install ran. Tested in Task 2.
- **A missing `.github/workflows/ci.yml` in the target repo must fail loudly with a clear message, not crash with a raw traceback or silently pass.** Tested in Task 1.

---

## Task 1: `scripts/hook_runner.py` -- non-interactive CLI over the existing contract

**Files:**
- Create: `skills/deliver/scripts/hook_runner.py`
- Test: `skills/deliver/tests/test_hook_runner.py`

**Interfaces:**
- Consumes: `parse_ci_steps`, `build_local_validation_contract`, `run_contract` from `scripts.validation_contract` (unchanged).
- Produces: `run_validation(repo_root: Path) -> int` (0 = all required steps passed, 1 = at least one required step failed or the workflow file is missing) and a `main(argv: list[str]) -> int` CLI wrapper (`argv[0]` is the repo root).

- [ ] Write a failing test asserting: (a) a real small git-repo fixture with a `.github/workflows/ci.yml` whose one step passes returns 0 from `run_validation`; (b) the same fixture with a step that exits non-zero returns 1; (c) a `continue-on-error: true` failing step still returns 0 (optional, not required); (d) a repo with no `.github/workflows/ci.yml` at all returns 1 with a clear printed message, not a traceback.
- [ ] Run it, confirm it fails with `ModuleNotFoundError`.
- [ ] Implement `run_validation` and `main` in `hook_runner.py`: read the workflow file (`try`/`except FileNotFoundError` around the read, printing a clear message and returning 1 on failure), call the three existing functions, print each contract entry's step name and pass/fail, return 1 if any `status == "required"` entry has `passed == False`, else 0. `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`.
- [ ] Run it, confirm all four cases pass.
- [ ] Commit.

## Task 2: `scripts/install_hooks.py` -- install/uninstall, worktree-safe, marker-checked

**Files:**
- Create: `skills/deliver/scripts/install_hooks.py`
- Test: `skills/deliver/tests/test_install_hooks.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (writes a shell script that calls `hook_runner.py` by path, but doesn't import it).
- Produces: `hooks_dir(repo_root: Path, run=subprocess.run) -> Path` (resolves via `git -C repo_root rev-parse --git-path hooks`). `install(repo_root: Path, deliver_root: Path, run=subprocess.run) -> list[str]` (writes `pre-commit` and `pre-push`, returns the list of hook names written; raises `HookConflictError` if either target path exists without this tool's marker comment). `uninstall(repo_root: Path, run=subprocess.run) -> list[str]` (removes only hook files carrying the marker, returns the list removed; leaves anything else untouched). `MARKER = "# installed-by: deliver-skill"` module constant.

- [ ] Write failing tests, each against a real git repo built in a tmp dir (matching this project's established convention): (a) `install` writes both hook files into the path `hooks_dir` resolves, each containing `MARKER` and an absolute path to `hook_runner.py`; on POSIX, each is executable (skip the executable-bit assertion on Windows, matching the git-editor-config precedent -- NTFS has no POSIX exec bit). (b) `install` raises `HookConflictError` and writes nothing when a pre-existing, non-marker `pre-commit` file is already there. (c) `uninstall` removes a marker-carrying hook but leaves a non-marker file at the other hook name untouched. (d) `install` then `uninstall`, invoked with `repo_root` set to a linked worktree created from the fixture repo, resolve to the SAME shared hooks directory as the main checkout (prove worktree-compatibility directly, not by assertion alone).
- [ ] Run, confirm `ModuleNotFoundError`.
- [ ] Implement `hooks_dir`, `install`, `uninstall`, `HookConflictError` in `install_hooks.py`. The written hook script body: `#!/bin/sh\n{MARKER}\nif command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi\n"$PY" "{hook_runner_abs_path}" "{repo_root_abs_path}"\nexit $?\n`.
- [ ] Run, confirm all pass.
- [ ] Commit.

## Task 3: Wire into SKILL.md and DISPOSITION.md, close the loop on the deferral

**Files:**
- Modify: `skills/deliver/SKILL.md`
- Modify: `skills/deliver/references/hooks-decision.md`
- Modify: `skills/deliver/DISPOSITION.md`

- [ ] Add a short new subsection to `SKILL.md` (near Section 6) describing the hook as an **optional, user-installed backstop** -- `deliver`'s own inline Section 6 step remains the actual enforcement; the hook exists for someone who wants a safety net against running `git commit`/`git push` by hand and bypassing the skill entirely. Document the exact install/uninstall calls.
- [ ] Update `hooks-decision.md`'s "deferred to #23" sentence to state it's now built, linking to the new scripts.
- [ ] Add a short section to `DISPOSITION.md` recording this as #23 item 1, closed.
- [ ] Run the full `skills/deliver` test suite once more, confirm green.
- [ ] Commit.

---

## Self-Review

**Spec coverage:** installable (Task 2 `install`), removable (Task 2 `uninstall`), delegates to the same contract (Task 1 reuses `validation_contract.py` unchanged), tested on POSIX and Windows-compatible-by-construction (shebang mechanism, Task 2's install writes one script that works on both; CI runs this repo's own suite on all three OS jobs), worktree-compatible (Task 2d), no silent global git config changes (install only writes files into the existing hooks dir, never touches `git config`).

**Review Focus:** all five items above have an owning task and a test.

**Proportion:** two small modules plus a docs task; no task's step list exceeds pinning its own function signatures and test cases.
