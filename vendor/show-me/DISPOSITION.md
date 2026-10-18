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
`skills` CLI's own valid `--agent` list). Re-checked live for #12 on
2026-10-18, not inferred from docs alone:

- **Claude Code**: `disable-model-invocation: true` works — official,
  documented behavior.
- **Codex**: `agents/openai.yaml`'s `allow_implicit_invocation: false` is
  upstream's own documented mechanism for this harness.
- **OpenCode**: **confirmed still broken, live, on the actually-installed
  version (1.19.0)** — not just inferred from the old GitHub issue.
  `opencode run "list every skill name you have available"` in a real
  test repo with show-me installed lists `show-me` right alongside every
  other skill, despite `disable-model-invocation: true`. The original
  upstream issue
  ([anomalyco/opencode#11972](https://github.com/anomalyco/opencode/issues/11972))
  was auto-closed for inactivity, not fixed, and comments continued
  reporting the bug for months after. A *newer* issue
  ([anomalyco/opencode#53172](https://github.com/anomalyco/opencode/issues/53172))
  was closed `COMPLETED` on 2026-10-06 with a maintainer comment citing a
  real merged fix
  ([PR #52747](https://github.com/anomalyco/opencode/pull/52747), merged
  2026-10-02) — but that fix is scoped to OpenCode's separate "V2 skills"
  catalog/config path, not the plain `.agents/skills/` convention this
  repo's skills (and most real-world installs) actually use. The paper
  trail reads like it shipped; the actual behavior for a normally-
  installed skill does not. Still an external, unresolved OpenCode
  limitation for this install path — not fixable from this fork — but
  now backed by a live repro, not an aging issue thread.
- **Antigravity: confirmed HONORED, live.** Installed show-me into the
  real global skills directory
  (`~/.gemini/config/skills/show-me/`, same mechanism `mp-code-review`/
  `skill-creator` already use there) and asked `agy` directly whether it
  had a `show-me` skill available: **"No."** Ruled out a stale-discovery
  false negative by adding a *fresh, unflagged* probe skill in the same
  directory at the same time — `agy` immediately reported that one as
  available ("Yes."), confirming freshness wasn't the reason show-me was
  hidden. Antigravity does respect `disable-model-invocation: true` for
  this install path, unlike OpenCode. The Cursor-forum-based suspicion in
  the original issue write-up undersold Antigravity; it's the one harness
  here that gets this right alongside Claude Code and Codex.

Tracked in #12 rather than silently shipped as if parity were
achieved. Three of four target harnesses now confirmed correct
(Claude Code, Codex, Antigravity); OpenCode remains a confirmed, external
gap for the plain `.agents/skills/` install path. Shipping as-is: the
remaining gap is outside this fork's control (an OpenCode product
limitation for this path), and holding the port on it would not change
the outcome.

### Partial, pragmatic mitigation

The skill body now opens with an explicit instruction: only act when the
user explicitly asked for this, regardless of whether the current harness
enforces manual-only invocation at the tool level. Unlike the frontmatter
flags above, this is plain instruction text every harness reads once the
skill is loaded, so it applies even where the flag is ignored.

This is a mitigation, not a fix, and the distinction matters:

- It reduces the chance the model actually *acts* (produces a diagram,
  pseudocode, or HTML) when not explicitly asked, on any harness.
- It does **not** stop the skill's name/description from being loaded
  into context on a harness that ignores the flag — the original
  complaint in the OpenCode issue (unnecessary context consumption) is
  unaffected by this change.
- It is a soft, model-followed instruction, not a hard, harness-enforced
  block — a model can still disregard it, which a real harness-level
  guard cannot.

## Eval comparison: original vs. adapted

Per this issue's "Improvement and evaluation" section, this reuses
skill-creator's qualitative output-comparison flow (paired baseline/candidate
subagents, not the trigger-eval harness — explicitly out of bounds for an
intentionally `disable-model-invocation: true` skill). Baseline = a snapshot
of the pristine upstream skill at the pinned commit; candidate = this fork.
Three cases, each run as a baseline/candidate pair, grounded in this repo's
actual code rather than invented examples:

1. **Code-flow explanation** ("how `sync-vendor.sh` resolves and applies its
   patch queue"). Both produced accurate, near-identical pseudocode/call-tree
   answers. Expected: the SKILL.md guidance for this case is byte-identical
   between baseline and candidate (only the HTML-diagram paragraph changed),
   so this is a regression check, not a behavior comparison — passed.
2. **Structural-change explanation** (commit `378e1b8`'s
   `sync-skill-creator.sh` → `sync-vendor.sh` generalization, in diff
   syntax). Same result: near-identical, accurate, format correctly chosen
   as diff syntax for a "change" case. Also a regression check — passed.
3. **Dense HTML-worthy example + its opening step**
   (`open_artifact.py`'s `detect_environment`/`opener_command` decision
   tree, as an HTML explainer). This is where the fork's actual change is
   exercised, and it's the one case with a real, triangulated difference:
   - **Baseline**, following upstream's literal instruction
     (`Bash(open path/to/show-me-{description}.html)`) verbatim, got: empty
     stdout, empty stderr, **exit code 4**. Confirmed independently three
     times — once directly by the agent doing this evaluation, once by the
     baseline subagent, and reproduced by that subagent a second time as a
     diagnostic — all on the same real headless WSL2 host, all identical.
     On this host `/usr/bin/open` happens to be a distribution alternative
     symlinked to `xdg-open` (not stock behavior everywhere: on a host with
     no `open` at all, the same instruction fails even more plainly with
     "command not found", exit 127); either way the instruction produces an
     opaque, silent, non-zero exit with zero information about what went
     wrong or whether the artifact even exists.
   - **Candidate**, running `open_artifact.py` on the identical artifact on
     the identical host: exit code **0**, printed the artifact's real path,
     and explained plainly that no opener is available in a `wsl` 
     environment lacking `wslview` — correctly detected, not guessed.
   - Both produced comparably well-constructed HTML (self-contained,
     dark/light-theme-aware, ~300-400 lines) — format selection and content
     quality are not where this case differs; the opening step is.

A sample candidate output (the HTML explainer from case 3, unmodified) was
published for direct visual inspection rather than only described.

Not covered by this comparison, and out of scope for it: the
non-invocation case (whether the skill stays silent unless explicitly
asked) wasn't re-tested here because no content this fork touches bears on
it — `disable-model-invocation`/`agents/openai.yaml` are byte-identical to
upstream by diff, so there is nothing for this fork to have regressed.
Genuine model/token/runtime measurements were not recorded as a benchmark
number, per the issue's instruction to record those "only when available"
— there is no meaningful quantity to benchmark here (no trigger rate, no
baseline-vs-candidate latency difference worth measuring for a one-shot
qualitative task).

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
- `/show-me` as an actually-*triggered* Claude Code skill (via a real
  `claude -p` subprocess, the mechanism #9's eval-validity work covers)
  was not exercised — only a direct, explicit "follow this SKILL.md"
  subagent invocation (see "Eval comparison" above), which is the
  qualitative flow this issue asks for and deliberately not the
  trigger-eval harness. The two test different things: #9's harness tests
  *whether* a skill gets invoked; this comparison tests the *quality* of
  what happens once it has been.
