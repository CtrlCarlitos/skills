# show-me fork: provenance and known gaps

Port for CtrlCarlitos/skills#1, Workstream B. Checked 2026-10-18 against
`humanlayer/skills` (upstream pin: `bba9d13ab34f0a87f1cc33df4dd196372393ddfc`,
2026-09-12, "Make show-me user-invocable" — confirmed the latest commit
touching this skill's path as of this check).

## What changed from upstream

Upstream's only "show the user the artifact" instruction is
`Bash(open path/to/show-me-{description}.html)` — macOS's `open` command,
with no fallback for any other platform. Upstream's own history
(`d3138e5`, "open HTML with Bash instead of task-artifact") shows they
deliberately moved away from a HumanLayer-product-specific inline-display
mechanism (`task-artifact`, tied to `.humanlayer/tasks/{task-slug}/...`)
to this generic `Bash(open ...)` precisely so the skill would work as a
portable skill across different coding agents, not just inside their own
product — the same reasoning behind this fork's own change, one step
further.

- Replaced the macOS-only `open` line with
  `python3 <skill-path>/scripts/open_artifact.py <path>`, a new,
  fully-tested module that detects the actual environment (native
  Windows, WSL, Linux desktop/headless, macOS desktop/headless,
  devcontainer) and only attempts an opener that's genuinely available
  there (`shutil.which`-gated, never assumed). A missing opener never
  loses the artifact, hangs, or gets retried — the file and its real path
  are the result either way. 23 unit tests, all pure/injectable (no
  mocking of global state): `skills/show-me/tests/test_open_artifact.py`.
- Added `LICENSE.txt` (MIT, HumanLayer © 2026, exact upstream text) and a
  fork note in `SKILL.md`, matching the `skill-creator` fork's convention.
- `disable-model-invocation: true` (Claude Code) and `agents/openai.yaml`
  (Codex, `allow_implicit_invocation: false`) are preserved verbatim from
  upstream — unchanged, not touched by this fork.

## What this fork does not fix: manual-invocation parity

This skill's entire design intent is to stay user-invoked only — "Do not
make every coding/design task generate a diagram or HTML file." That
intent is **not uniformly honored** across this repo's four target
harnesses (`claude-code`, `codex`, `opencode`, `antigravity`, per the
`skills` CLI's own valid `--agent` list):

- **Claude Code**: `disable-model-invocation: true` works — official,
  documented behavior.
- **Codex**: `agents/openai.yaml`'s `allow_implicit_invocation: false` is
  upstream's own documented mechanism for this harness.
- **OpenCode**: confirmed via a live, still-open upstream issue
  ([anomalyco/opencode#11972](https://github.com/anomalyco/opencode/issues/11972),
  multiple independent reports) that OpenCode currently **ignores**
  `disable-model-invocation` entirely — the skill stays visible to the
  model regardless. The only workaround is the *user's own* OpenCode
  permission config (`opencode.json`'s `permission.skill` block), which a
  skill package cannot set on a user's behalf. This is an external,
  unresolved OpenCode limitation, not something fixable from this fork.
- **Antigravity**: no confirmed mechanism found either way. It shares the
  `.agents/skills/` convention with Cursor, where the same
  `disable-model-invocation` flag is also reportedly ignored (per a
  Cursor forum report) — suggestive, not confirmed, for Antigravity
  specifically. Not tested directly.

Tracked in #12 rather than silently shipped as if parity were
achieved. Shipping now regardless: the gap is external to this fork (an
upstream OpenCode feature request, an unverified Antigravity detail), and
holding the whole port on it would not change either outcome.

## What was not tested

- A native macOS or Windows runtime smoke test of the opener actually
  launching a real browser window was not performed — CI runners on all
  three OSes are headless, so "did a browser visibly open with content"
  isn't verifiable from any CI runner, on this skill or skill-creator's.
  `detect_environment`/`opener_command`/`try_open` are unit-tested
  (including one real-subprocess test with no mocking: launching a
  genuinely nonexistent command must return `False`, not raise), and the
  same test suite runs on real Ubuntu/Windows/macOS CI for per-OS signal
  on path handling and tool detection — not on whether a GUI appeared.
- Devcontainer behavior (logic + a unit test for the `devcontainer`
  classification) has no CI coverage — no devcontainer CI runner exists
  for this repo.
- `/show-me` as an actually-triggered Claude Code skill, end-to-end
  (model picks the right visual format, writes a real HTML file, the
  opener runs against it) was not run live in this session — that would
  require a real `claude -p` invocation, which the eval-validity work in
  #9 already covers the harness-level correctness of; this port adds the
  opener, which is the part #9's tooling never needed to test.
