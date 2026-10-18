---
name: deliver
description: Coordinate a task from read-only discovery through an authorized, confirmed PR merge and safe cleanup -- the two-gate lifecycle (discovery -> authorized documentation -> authorized implementation), a repo-owned local-validation contract before every CI-triggering push, and the push-through-cleanup tail (diagnose/fix red CI, squash-merge when authorized, confirm merge, clean up) that existing skills stop short of. Use when the user says "deliver", "implement and ship", "take this through to merged", or asks to resume/finish a task already in progress -- never as competing planning/TDD/debugging logic, and never as implicit permission to push, merge, or delete anything.
---

A thin coordinating layer over this project's existing skills, not a competing methodology. It invokes `superpowers:brainstorming`, `writing-plans`, `executing-plans`/`subagent-driven-development`, `test-driven-development`, `using-git-worktrees`, `verification-before-completion`, and `finishing-a-development-branch` at the right points, and adds only what's genuinely missing between them. Read `references/compatibility-map.md` once, in full, before using this skill the first time in a session -- it records exactly which skill owns which responsibility and where this skill picks up.

**The gap this skill actually fills:** nothing installed here takes a task past "push, open a PR" through diagnosing and fixing red CI, a squash-merge once authorized, confirming the merge landed, and safe cleanup -- `finishing-a-development-branch`'s own Option 2 stops at "PR created" by design. And nothing defines a repo-owned mapping from what CI actually runs to the exact local command to run before pushing. Those two things are this skill's real content; everything else below is coordination.

## The three states

| State | Allowed | Not allowed |
|---|---|---|
| **Discovery** | Read code/docs/issues/history/logs; research; compare approaches; ask questions; present findings in conversation | Any repository or connected-service mutation. Branch/worktree creation is a mutation -- do not create one yet. Commands used to reproduce/inspect behavior are not automatically read-only (a test run, a build, a DB query can all write) -- check what a command actually does, not just why you're running it. |
| **Authorized documentation** | Write only the agreed findings, spec, plan, or tracker record | No application code, test, dependency, or config changes. Permission to write a spec or file an issue is not permission to implement it. |
| **Authorized implementation** | Modify the approved scope in the task's isolated workspace, per its delivery policy | Scope beyond what was approved -- a material scope change returns to the relevant gate instead of silently expanding. |

A research/brainstorming skill's *name* doesn't tell you its side effects -- `superpowers:brainstorming` is read-only by its own description, but verify any other investigation skill the same way before trusting it in discovery. An explicitly authorized experiment that needs writes happens in a disposable environment; approving the experiment is not approving its code for the real task.

## Gate 1 -- after investigation, research, or brainstorming

Answer: **what did we learn, what's decided, what happens next?**

Capture: the problem and current behavior with the sources that back it; the recommended approach and real alternatives/tradeoffs/scope/exclusions; testable acceptance criteria and open questions; the next action (no change needed / more research / authorized docs or tracker work / planning / implementation-readiness review).

Read existing issues/specs before proposing new ones (same discipline this project's own sessions already follow: check `gh issue list`/`gh issue view` live rather than trust memory). Writing a spec or filing an issue is never, by itself, authorization to implement it -- say so explicitly when handing off, so a fresh session or a different agent doesn't infer authorization that was never given.

## Gate 2 -- immediately before implementation

Answer: **are we ready and authorized to change the right system in the right way?**

Check: approved scope, an applicable plan, testable acceptance criteria, no unresolved decision that would change the implementation; the correct repo/base branch and whether a task-owned branch/worktree already exists (reuse it -- `using-git-worktrees` Step 0 already detects this, don't re-detect it badly); that your actual editor/shell session is operating in that workspace, not just that a worktree was created or a `cd` was run once; the repo's real verification commands and known baseline failures (discovered read-only; any baseline mutation needs its own authorization); and the authorized endpoint for this task -- implementation only, stop at the PR, or continue through an eligible merge and cleanup.

**The first failing test is implementation, and belongs after this gate**, not before it. If you're resuming work and TDD evidence from an earlier session is missing, report that gap -- never invent evidence that red-green happened if you didn't watch it.

An existing approval covers the task/revision it was actually given for -- an unrelated prior approval, an issue merely existing, or a standing workflow preference is not unlimited write/merge authority for this specific change.

## Local validation contract (Section 6)

Before the first CI-triggering push, and before every repair push after it: build and run the repo's own validation contract rather than hand-maintaining a second list that drifts from CI.

```python
from scripts.validation_contract import parse_ci_steps, build_local_validation_contract, run_contract

steps = parse_ci_steps(Path(".github/workflows/ci.yml").read_text())
contract, ci_only = build_local_validation_contract(steps)
results = run_contract(contract, repo_root)
```

- `ci_only` entries (a `uses:` action step like `actions/checkout`) have no local equivalent -- report them as a documented CI-only reason, never as a silent gap.
- Each `contract` entry already carries the exact command and working directory CI runs -- there is no separate "local version" to maintain; drift is structurally impossible as long as the contract is rebuilt from the current workflow file, not cached from an earlier run. On Windows, `run_contract` routes through `pwsh` explicitly rather than Python's own `shell=True` default (`cmd.exe`) -- confirmed live on windows-latest CI that GitHub Actions' `run:` steps there actually execute through PowerShell, not cmd, so reproducing them through the wrong shell can silently pass or fail on different syntax than CI really ran.
- A `continue-on-error` CI step becomes `status: "optional"` -- a required-check failure blocks the push; an optional one doesn't, but still gets reported, not silently dropped.
- **Evidence must always be for the tree you are about to push right now -- never an earlier revision, a different staged/unstaged state, a stale checkout, or a result from earlier in the conversation.** This is a general rule, not just an autofix special case: anything that can change the tree between a validation run and the actual push -- a formatting/autofix pass, a review fix, an intervening edit, or simply time passing in the conversation since the last run -- means the contract gets **re-run before trusting it as current**. If you cannot prove zero changes happened since the last run, re-run it; don't reason your way to treating an old pass as still valid. Formatting/autofix is itself a write and belongs in authorized implementation -- inspect the diff for unrelated reformatting, then re-run under this same rule.
- A missing tool, a skipped check, or an infra failure during this step is not a pass -- `superpowers:verification-before-completion`'s Iron Law applies directly here: no completion or "ready to push" claim without having actually run the contract on the current tree and read its output.
- Pending/missing/cancelled/empty results are not success either, on this step or on the real CI run after pushing.

See `references/hooks-decision.md` for why this is a skill-level step rather than a Git hook in this repository (short version: no existing hook infrastructure here, and a hook would duplicate enforcement `deliver` already provides as part of its own flow -- an installable hook is deferred to #23 for anyone who wants a backstop against skipping the skill itself).

## Push through confirmed, safe cleanup (Section 9)

This is the part `finishing-a-development-branch` stops short of by design. Once that skill's Option 2 has pushed and opened the PR, and the task's authorized endpoint extends past "stop at the PR":

1. Watch CI (e.g. `gh pr checks <N>` polling, or this project's own Monitor-loop pattern). Pending/missing/cancelled/empty is not green.
2. On red: diagnose the actual failure (read the real CI log, don't guess from the job name), fix it, **re-run the local validation contract on the fixed tree**, then push the fix. Bound repair attempts -- report an infrastructure/credential/permission blocker rather than looping on it. Never disable a test, weaken a check, or use a skip-CI marker to manufacture green.
3. Once every required check and applicable review/merge requirement is satisfied for the current PR revision (not an earlier one), and the task's authorization covers merging: squash-merge (prefer squash where the repo permits it; no administrator bypass). Auto-merge being enabled, or merge-queue entry, is not a confirmed merge -- keep task resources until you've actually confirmed it landed (`gh pr view <N> --json state,mergedAt`, not an assumption from a green check run).
4. After confirmed merge: clean up only this task's own branch/worktree, from outside the worktree, the same way this project's sessions already do it (`git push origin --delete <branch>`, then the worktree-removal tool with `discard_changes` only after confirming nothing valuable is uncommitted there). Never force-delete on an ancestry mismatch without showing what's at stake and asking, mirroring `finishing-a-development-branch`'s own refusal-then-ask pattern for a non-empty worktree.
5. Report one of: **blocked**, **PR open**, **merge pending**, **merged / cleanup blocked**, or **complete** -- with the actual commands/results, the tested revision, the PR reference, the CI evidence for the final revision, confirmed-merge evidence, and cleanup results or exactly what was preserved and why.

If Standards/Spec review is part of this task's policy, invoke `mp-code-review` (#7) before this section's merge step -- `deliver` does not run a second, competing review.

## Invocation and enforcement

See `references/cross-harness.md` for the illustrative entry points, the resume/finish contract, and -- separated explicitly -- what each harness is confirmed, live, to actually enforce versus what `deliver`'s own prose merely instructs (#24; all four harnesses now live-confirmed, with real gaps found for Antigravity and OpenCode's unconfigured default). Saying "deliver issue #123" selects the workflow; it is never by itself permission to push, merge, or delete -- that authorization is Gate 2's question, answered per task.

## What this skill does not do

- Does not reimplement brainstorming, planning, TDD, debugging, or branch-finishing logic that `superpowers:*` already owns -- see `references/compatibility-map.md` for the exact handoff.
- Does not adopt `setup-matt-pocock-skills` or Matt Pocock's tracker conventions, even partially -- follows whatever tracker/spec convention the repo already demonstrates, the same fallback chain `mp-code-review` (#7) uses.
- Does not run a second, competing code review -- coordinates with `mp-code-review` (#7) instead.
- Does not treat "deliver" as blanket merge authority, an existing issue's mere existence as implementation authorization, or a green optional check as a required one.
- Does not provision containers, rehearse via `act`, or provision OS/desktop test infrastructure -- see `references/containers-act-os-profiles.md` for the decision and `#23` for the deferred research.
- Does not claim cross-harness enforcement parity from installation alone -- confirmed live, not assumed, that it genuinely doesn't exist (Codex: real OS-level discovery enforcement if configured; OpenCode: none by default; Antigravity: no comprehensive equivalent on its headless CLI) -- see `references/cross-harness.md` and `#24`.
