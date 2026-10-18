# skill-creator fork: patch disposition

Audit for CtrlCarlitos/skills#1, Workstream A. Checked 2026-10-17 against
`anthropics/skills` (upstream pin: `33375500bcea98d610eb30ce10ac4e59b89c390d`,
2026-09-24).

## Rebase decision: no rebase

- `anthropics/skills#1827` (the bug patch 0001/0002 work around) is still
  **open, 0 comments** as of 2026-10-17. No upstream fix exists to adopt.
- The `skills/skill-creator` subtree has had no skill-creator-specific
  commit upstream since **2026-04-20** (PR #547), which predates our
  2026-09-24 pin. There is nothing newer to rebase onto.
- Conclusion: the pin stays at `33375500bcea98d610eb30ce10ac4e59b89c390d`.
  Revisit if/when #1827 closes upstream.

## Patch disposition table

| Patch | Original purpose | Upstream equivalent? | Decision | Evidence |
|---|---|---|---|---|
| `0001-windows-pipe-reader.patch` | `select.select()` only accepts sockets on Windows; every query failed with `WinError 10038`. | None (#1827 open). | **Retain.** | #1827 open; regression test added (`tests/test_pump_stdout_to_queue.py`), extracted the pump into a testable `pump_stdout_to_queue()`. |
| `0002-utf8-file-io.patch` | Non-ASCII report content (U+2717) crashed on a cp1252 locale; every `read_text`/`write_text`/`open` needed explicit `encoding="utf-8"`. | None (#1827 open; same issue covers this). | **Retain.** | Static regression test (`tests/test_utf8_file_io.py`) scans the vendored source for any text I/O call missing `encoding=`, so a future edit can't reintroduce the bug. |
| `0003-project-root-and-real-skill-trigger.patch` | `find_project_root()` walking up from cwd lands in the wrong place when run outside a project; the trigger detector only accepted its own decoy name, missing a real installed skill's own invocation. | None found. | **Retain.** | Regression test (`tests/test_find_project_root.py`) covers discovery, fallback, and the `--project-root` override. |
| `0004-fork-note.patch` | Documents the fork, upstream pin, and tracking issue in `SKILL.md`. | N/A (repo-specific note, not a behavior fix). | **Retain.** | No upstream equivalent possible; this is our own provenance note. |
| `0005-regression-tests-and-eval-fixes.patch` | New: two eval-validity bugs found during this audit (see below) plus regression coverage for 0001-0003's actual responsibilities. | N/A (new). | **Add.** | See "New findings" below. |

## New findings (addressed in patch 0005)

Reading `run_eval.py`/`run_loop.py` while auditing eval validity (issue
point 5) surfaced two real bugs, not just the suspicion the issue raised:

1. **Contaminated results.** The trigger detector accepted a match on
   either the unique per-run decoy name or the bare real `skill_name`
   (added in 0003, to catch a genuinely-installed skill invoking itself by
   its real name). If a real skill with that name is *also* installed in
   the target project, the model can trigger that unrelated, already-shipped
   copy instead of the injected candidate description, and the harness
   can't tell the two apart — it reports a pass for the candidate anyway.
   Fixed by detecting the collision (`find_conflicting_installed_skill`)
   and surfacing it loudly (stderr warning + `eval_validity_warning` field
   in the JSON output) rather than silently contaminating the score.

   Considered and rejected: automatically moving the real installed copy
   aside for the run's duration. No verified, documented mechanism exists
   to isolate Claude Code's skill discovery without either disabling the
   decoy too (`--disable-slash-commands` disables *all* skills) or
   mutating the user's real `~/.claude/skills/` directory on disk — a risk
   if the process crashes mid-run. Flagging loudly is the honestly-scoped
   fix for this change; automatic isolation is a candidate follow-up if a
   safe primitive is confirmed later.

2. **Infra failures counted as 0%.** Any worker exception (subprocess
   crash, missing `claude` CLI, timeout) was caught and appended as a plain
   `False` — indistinguishable from the model genuinely not triggering.
   `aggregate_results`/`summarize` now report an `errored` count separate
   from `passed`/`failed`, and `run_loop.py`'s `all_passed` early-exit no
   longer fires when a run has errored queries.

## What this audit did not change

- Packaging/validation with spaces and non-ASCII paths: tested
  (`tests/test_spaces_and_unicode_paths.py`) and already correct — no bug
  found, now covered by a regression test.
- `scripts/sync-skill-creator.sh` (maintainer-only, not part of the
  vendored subtree) had a real macOS portability bug: `diff -r
  --strip-trailing-cr` uses a GNU-diffutils-only flag that stock macOS's
  BSD `diff` rejects outright, so `--check` never ran on a Mac without
  Homebrew coreutils. Fixed by switching to `git diff --no-index
  --ignore-cr-at-eol` — same `git` binary on every platform this script
  already requires. Covered by `scripts/tests/test_sync_skill_creator.sh`.
- Fixing the diff portability bug also revealed that `--check` had been
  silently blind to file-mode drift: `diff -r` never compares permission
  bits, so when 7 of the vendored scripts quietly lost their executable
  bit relative to upstream, nothing caught it. Re-applied `chmod +x` to
  match upstream exactly (`utils.py` and `__init__.py` stay non-executable,
  matching upstream).
- Cross-agent execution parity (Claude Code vs. Codex/OpenCode/Antigravity)
  for the evaluation subprocess (`claude -p ...`) was **not** tested here:
  `run_eval.py`/`run_loop.py` hard-depend on the `claude` CLI specifically.
  Installing skill-creator for another harness does not make its
  description-optimization loop run there; this is an existing, documented
  limitation, not something this patch changes or newly claims to fix.
- Native Windows and macOS runtime smoke tests were not performed — this
  session only has WSL/Linux. The Windows pipe-reader and macOS diff fixes
  above are verified by direct unit tests of the extracted logic
  (`pump_stdout_to_queue`, the `git diff --no-index --ignore-cr-at-eol`
  invocation itself), not by running `claude -p` on those platforms.
