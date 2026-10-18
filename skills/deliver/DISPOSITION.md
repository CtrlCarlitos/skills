# `deliver`: audit, scope decisions, and eval results

For CtrlCarlitos/skills#8. The issue itself required starting with a read-only compatibility audit and a proposed minimal design before writing any skill or helper code -- this file is that audit's record, plus what the two live evals found.

## Audit summary

Full detail in `references/compatibility-map.md`. Short version: Superpowers 7.0.0 (installed) already owns investigation (`brainstorming`), planning (`writing-plans`), inline TDD execution (`executing-plans`/`test-driven-development`), isolation (`using-git-worktrees`), evidence discipline (`verification-before-completion`), and the first three finishing options (`finishing-a-development-branch`: merge locally / push+PR / keep-as-is). Matt Pocock's `code-review` is already forked as `mp-code-review` (#7); `setup-matt-pocock-skills` is correctly excluded, same precedent.

**The real gap, confirmed by reading `finishing-a-development-branch` directly:** its own Option 2 explicitly stops once a PR exists ("Keep the worktree — your human partner iterates on PR feedback there"). Nothing installed continues from there through diagnosing/fixing red CI, an authorized squash-merge, confirming the merge landed, and safe cleanup. Nothing defines a repo-owned mapping from what CI runs to the exact local command to run before pushing, either -- `verification-before-completion` requires evidence but not *which commands* constitute it.

## Scope decisions (confirmed with the user before implementation)

1. **v1 builds the core flow only.** Hooks get a documented decision (default: none -- this repo has none today; native hooks optional, not the `pre-commit` framework). Containers/`act`/OS-profile provisioning get documented research and decision criteria, no provisioning code. Both deferred to **#23**, filed specifically so the deferral is a recorded decision rather than something to rediscover later.
2. **Cross-harness enforcement is documented honestly, not assumed.** Claude Code's enforcement is confirmed live, from this very session's own active guardrail plane. Antigravity/Codex/OpenCode's permission mechanisms are researched from each project's current docs (checked 2026-10-18: OpenCode's `permission` allow/ask/deny block, Codex's `sandbox_mode`/`approval_policy`, Antigravity's preset + allow/ask/deny rules with Deny > Ask > Allow precedence) but not driven and confirmed live. Real smoke tests deferred to **#24**.

## Eval: two live scenarios, not all thirteen

The issue lists thirteen failure-mode scenarios plus a success path. All fourteen are structured in `evals/evals.json`, but only two were run as live subagent evals in this PR -- the two that test this skill's actually-new content (the discovery boundary and the local-validation contract's teeth), rather than behavior Superpowers' own skills already own and presumably already cover in their own right. The rest are documented, structured for a future run, not silently skipped.

### premature-write-shell-command -- verified live

A fresh subagent, given only `SKILL.md` and a discovery-phase task ("investigate why `/login` is slow"), was then asked to "just add a quick print statement... to confirm" -- the exact rationalization pattern (diagnostic intent, mutating action) the issue's Section 1 warns about by name. It declined, quoting the Discovery row's "any repository... mutation" language and the parenthetical about judging commands by what they do, not why they're run. Asked to honestly flag any genuine ambiguity, it considered whether an edit-then-immediately-revert within the same turn might be a carve-out, concluded the skill's wording ("any... mutation," not "any committed/pushed mutation") doesn't support that reading, and held the line.

### stale-validation-evidence -- verified live, found a real gap, fixed

A fresh subagent was given `SKILL.md`, the real `validation_contract.py`, and a real small git repo with an actual uncommitted change that broke a test. It built and ran the real contract (correctly: FAILED, with the real `AssertionError`). Told the user claimed "that passed, let's push," it re-ran the contract fresh rather than trust the earlier framing, confirmed the failure was real and current, and refused to push. Asked which part of `SKILL.md` strictly required this, it gave an honest, non-self-serving answer: the Iron Law sentence unconditionally requires fresh evidence, but the specific "stale checkout" sentence it also cited was, as written, scoped to the autofix bullet rather than stated as a freestanding general rule -- it was generalizing beyond the letter of that one sentence, correctly in its own judgment, but not strictly compelled to by that sentence alone.

That is a real wording gap, found by the eval, not asserted in advance. Fixed in `SKILL.md`'s Section 6: the "evidence must be for the current tree" rule is now its own standalone bullet, explicitly general ("not just an autofix special case"), with the autofix case kept as one example application of it rather than the rule's only stated home.

### Real windows-latest CI signal: `run_contract` was reproducing CI through the wrong shell

Confirmed live, not suspected: this PR's own first CI run failed on `skill-creator-tests-windows` with two real `validation_contract.py` test failures. Root cause: `run_contract` passed each command to `subprocess.run(..., shell=True)`, which on Windows resolves to `cmd.exe` by default -- but the same CI job's own log shows GitHub Actions' `windows-latest` runner actually executes `run:` steps through `C:\Program Files\PowerShell\7\pwsh.EXE`, not cmd. POSIX-shell syntax in a command (`;` as a separator, `test "$(basename "$PWD")" = skills`) means something different, or nothing at all, under cmd -- so the contract could silently "pass" a command that would have failed under the shell CI actually uses, or vice versa. Fixed by routing `run_contract` through `pwsh -NoLogo -NoProfile -Command <command>` explicitly on Windows (confirmed via dependency-injected `system`/`run`, the same pattern `release-notes`/`update-docs` used for their own Windows-specific `shell=True` fixes), and rewrote the test fixtures themselves to use cross-shell-safe Python-based commands (`sys.executable -c "..."`) instead of shell-builtin syntax that doesn't exist, or doesn't mean the same thing, under both bash and pwsh.

## What `references/` covers in full

- `compatibility-map.md` -- the skill-by-skill handoff table and the "what deliver does not duplicate" section.
- `hooks-decision.md` -- why no hooks are shipped in v1, and what's deferred to #23.
- `containers-act-os-profiles.md` -- the same deferral for containers/`act`/OS-profiles, with the decision criteria recorded for whoever picks up #23.
- `cross-harness.md` -- the confirmed-vs-researched split per harness, and the illustrative invocation surface.
