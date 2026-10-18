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
  vendored subtree; generalized into `scripts/sync-vendor.sh <name>` when
  the `show-me` port added a second vendored skill) had a real macOS
  portability bug: `diff -r --strip-trailing-cr` uses a GNU-diffutils-only
  flag that stock macOS's BSD `diff` rejects outright, so `--check` never
  ran on a Mac without Homebrew coreutils. Fixed by switching to `git diff
  --no-index --ignore-cr-at-eol` — same `git` binary on every platform this script
  already requires. Covered by `scripts/tests/test_sync_skill_creator.sh`.
- Fixing the diff portability bug also revealed that `--check` had been
  silently blind to file-mode drift: `diff -r` never compares permission
  bits, so when 7 of the vendored scripts quietly lost their executable
  bit relative to upstream, nothing caught it. Re-applied `chmod +x` to
  match upstream exactly (`utils.py` and `__init__.py` stay non-executable,
  matching upstream).
- Cross-agent execution parity (Claude Code vs. Codex/OpenCode/Antigravity)
  for the evaluation subprocess (`claude -p ...`) was **not** tested in
  this original audit: `run_eval.py`/`run_loop.py` hard-depended on the
  `claude` CLI specifically. **Resolved for Codex and OpenCode in
  CtrlCarlitos/skills#10** — see "Cross-agent eval parity" below. Still a
  documented, reasoned limitation for Antigravity specifically, not
  fixed.
- A native macOS runtime smoke test was not performed — this session only
  has WSL/Linux, and GitHub-hosted macOS runners weren't added to CI. The
  macOS diff fix is verified by a direct unit test of the `git diff
  --no-index --ignore-cr-at-eol` invocation itself, not by running it on
  macOS.

## Update: real `windows-latest` CI signal (same PR)

A `windows-latest` CI job was added and, on its first real run, caught
three genuine bugs no amount of WSL/Linux-only testing would have found
— confirming the honest-scoping decision above was the right call, not
just caution for its own sake:

1. **`test_find_project_root`'s tests errored tearing down.**
   `tempfile.TemporaryDirectory()`'s cleanup ran while cwd was still
   inside it — POSIX allows removing a directory you're `cd`'d into,
   Windows doesn't (`PermissionError: [WinError 32]`). The chdir-back was
   deferred to `addCleanup`, which fires *after* the `with` block's
   cleanup already ran. Fixed by switching to `tempfile.mkdtemp()` with
   its own `addCleanup(shutil.rmtree)` registered before the chdir-back's
   — cleanups run LIFO, so cwd is restored first.
2. **`ModuleNotFoundError: No module named 'yaml'`.** `quick_validate.py`
   imports PyYAML, but neither this repo nor upstream ever declared it as
   a dependency; it only "worked" by the accident of Ubuntu's base image
   happening to have it preinstalled. Added `requirements.txt` (confirmed
   via an AST scan to be the only third-party import in the whole tree)
   and a `pip install -r` step in both CI jobs.
3. **`UnicodeEncodeError` printing status emoji.** `package_skill.py`
   prints checkmarks/crosses via plain `print()`, which raises on
   Windows' default console encoding (cp1252) — the same bug class as
   patch 0002's file-I/O fix, just for stdout. Reproduced deterministically
   on *any* OS (not only verified via remote Windows CI) by redirecting
   `sys.stdout` to a cp1252-encoded stream in a test, confirming the exact
   traceback locally before fixing. Fixed by reconfiguring stdout to UTF-8
   at entry.

All three are now fixed and covered by regression tests; the Windows job
is green. One thing was *not* fixed, deliberately: the `--check` step
(file-mode comparison) genuinely fails on Windows —
`git-for-Windows`/NTFS doesn't track Unix executable bits the way Linux
does, so the comparison reports a mismatch even when file content is
identical. This is kept in CI as `continue-on-error: true` for
visibility, never promoted to a required check.

Cross-agent execution parity for the evaluation subprocess was, at the
time this Windows CI work landed, still not tested beyond the `claude`
CLI — see "Cross-agent eval parity" below for how that gap was closed
for Codex and OpenCode, and the reasoned limitation recorded for
Antigravity, in CtrlCarlitos/skills#10. None of CI's credentials changed:
the new adapters' live-round-trip tests are gated on the relevant CLI
being installed (`shutil.which`), same pattern as the existing
Claude-only tests that never ran on CI either.

## Cross-agent eval parity (CtrlCarlitos/skills#10)

Checked each target harness's actual non-interactive, structured-output
capability directly (not assumed from memory), by capturing a real event
stream from each against a real skill in a real repo:

- **Codex** (`codex exec --json`): no discrete skill tool at all. A
  skill load shows up as an `item.completed` / `command_execution` event
  whose `command` field is literally `cat <path>/<skill-name>/SKILL.md`.
  Confirmed live, then built as `_run_single_query_codex` +
  `_codex_event_indicates_trigger`.
- **OpenCode** (`opencode run --format json`): the cleanest signal of
  the three — a discrete `tool_use` event with `part.tool == "skill"`
  and `part.state.input.name` equal to the skill's name. Structurally
  the same idea as Claude's own `Skill` tool, just shaped differently.
  Confirmed live, then built as `_run_single_query_opencode` +
  `_opencode_event_indicates_trigger`.
- **Antigravity** (`agy --output-format stream-json`): also has a real,
  clean signal (a `view_file` tool call with `AbsolutePath` pointing at
  the skill's `SKILL.md` — confirmed live while investigating #12). **No
  adapter was built here, for a specific, confirmed reason, not a vague
  "unverified":** both Codex's and OpenCode's adapters rely on writing a
  throwaway, uniquely-named proxy skill under the *project-local*
  `.agents/skills/` directory per eval query, the same trick
  `_run_single_query_claude` already uses with `.claude/commands/`. Live
  testing for #12 established that Antigravity does **not** reliably
  discover project-local `.agents/skills/` skills at all in this
  environment — only its real *global* skills directory
  (`~/.gemini/config/skills/`) is actually read. A working Antigravity
  adapter would therefore need to write and remove a throwaway skill in
  the user's real global skill directory on *every single eval query* —
  a materially more invasive mechanism than the other two harnesses need,
  and not one this project is willing to do silently inside an
  automated evaluation loop. If Antigravity ever supports project-local
  skill overrides (an `--add-dir`-style flag was tried and did not help;
  a per-project settings override was not found), building this adapter
  becomes straightforward with the same architecture as the other two.

### Architecture: adapters, not three near-duplicate scripts

`run_single_query` is now a thin dispatcher over `_HARNESS_ADAPTERS`
(`claude`, `codex`, `opencode`); `main()` gained a `--harness` flag
(default `claude`). Everything downstream of `run_single_query` —
worker pooling, `aggregate_results`, the errored/failed/passed
distinction, CLI reporting — is completely unchanged and harness-
agnostic; it already operated purely on the bool/exception contract
every adapter returns. `_run_single_query_claude`'s own body is
byte-for-byte unchanged from before this issue — zero risk to the
already-shipped, tested Claude path. The two new adapters share a small
amount of genuinely common infrastructure
(`_read_json_lines_with_timeout`, the same select()/Windows-queue-reader
split `_run_single_query_claude` already used, and
`_write_proxy_agents_skill` for the `.agents/skills/` throwaway-skill
trick both Codex and OpenCode need) without retrofitting that onto
Claude's own proven read loop.

`find_conflicting_installed_skill` also now takes a `harness` parameter:
for Codex/OpenCode it checks `.agents/skills/<name>/SKILL.md` instead of
Claude's `.claude/skills/<name>/SKILL.md`. The failure mode differs by
direction from Claude's own documented risk — a same-named real skill
installed alongside the throwaway, uniquely-suffixed proxy shows up as a
**false negative** for Codex/OpenCode (the model reasonably uses the
real skill instead of the test's oddly-named proxy, so the proxy's
unique name never fires) rather than Claude's **contaminated
measurement** risk (a same-named decoy *command* could plausibly be
confused with a same-named real *skill*). Checked eagerly either way,
same as before.

### A real OpenCode reliability finding, not a hypothesis

Building the live integration test for the OpenCode adapter surfaced a
genuine, severe reliability problem in `opencode run` itself, confirmed
across many repeated attempts, different flag combinations
(`--print-logs`, `--log-level DEBUG`), and even a brand-new, completely
uncluttered test directory (ruling out interference from this session's
own accumulated test fixtures): `opencode run` frequently produces **zero
stdout** and hangs indefinitely right after its own internal `"init"` log
line, in a clear majority of attempts in this environment. When it
doesn't hang, the real skill-trigger event fires within about a second of
the process actually producing output — so the adapter's own detection
logic (proven separately against real captured event fixtures in
`tests/test_harness_adapters.py`) is not what's slow; `opencode run`
itself is unreliable here.

This does not block shipping the OpenCode adapter: `run_eval.py`'s
existing errored/failed/passed design (predating this issue, built for
Claude) already treats a timed-out run as an **error**, never averaged
in as a non-trigger, and `--runs-per-query` already retries. A `codex`/
`claude` evaluation run is unaffected. An `opencode` evaluation run may
simply report a higher error rate than the other two harnesses for
reasons outside this project's control — that should be read as
"opencode had trouble running," not "the description doesn't trigger
opencode." The live round-trip test for this specific case
(`RealOpencodeAdapterTests.test_a_query_that_should_trigger_the_skill_does`)
retries several times and **skips**, rather than fails, if every retry
is swallowed by the hang — asserting against a majority-broken external
CLI would make the test chronically red for a reason this project can't
fix, which is worse than an honest skip with a clear reason.
