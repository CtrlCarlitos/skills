---
name: deliver
description: Carry an authorized task through implementation, fixing red CI, merging on green and safe cleanup. Use when the user says "deliver", "implement and ship", "take this through to merged", gives a standing merge/fix/cleanup instruction, or asks to resume/finish delivery. Preserve the authorized endpoint across turns; honor design-only and stop-at-PR limits. Coordinate existing planning/TDD/debugging skills and Guardrail's repository authorization.
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

### Task authorization and enforcement

For an approved implementation task, an explicit `/deliver`, "implement and ship",
"take this through to merged", or applicable "fix on red, merge on green, clean up
on merged" instruction authorizes that task's delivery endpoint. Continue through
validation, push/PR, CI repair, eligible merge and safe task cleanup. Record the
authorization basis and endpoint with the task's repository, branch/worktree, PR
and current head; retain them across turns, compaction and resume. Recheck the live
resources when resuming; continue the existing task rather than requesting the
same authorization again or creating a duplicate branch/PR.

An explicit narrower endpoint wins: investigation/design-only authorizes that
work; "stop at the PR" stops there. Material scope expansion, bypassing a required
check/review, or discarding valuable work needs a fresh operator decision. An issue
merely existing, an unrelated approval or model-written task notes grant nothing.

Guardrail's **repository authorization** is separate from task intent. The operator
enables bounded delivery once per repository; an agent cannot enable it from prose,
an Overlay or a skill. When available, inspect `guardrail delivery status` and use
the bounded executor below. Missing support/authorization is an enforcement blocker,
not missing conversational consent: report the exact setup or approval needed and
preserve the task endpoint. Follow every Guardrail ask/deny; task authorization does
not authorize a workaround.

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

See `references/hooks-decision.md` for why this is a skill-level step rather than a Git hook by default (short version: no existing hook infrastructure in this repository, and a hook would duplicate enforcement `deliver` already provides as part of its own flow). An optional, user-installed `pre-commit` + `pre-push` hook pair now exists as a backstop against running `git commit`/`git push` by hand and bypassing the skill entirely -- it delegates to the exact same contract via `scripts/hook_runner.py`, never a second implementation, and resolves the repo root at *runtime* (not install time), so it validates the right tree regardless of which worktree the commit actually happens in:

```bash
# From anywhere -- repo_root and deliver_root both default sensibly
# (repo_root: cwd; deliver_root: this script's own skill directory).
python3 -m scripts.install_hooks install [repo_root] [deliver_root]
python3 -m scripts.install_hooks uninstall [repo_root]
```

`install` refuses (raises `HookConflictError`) rather than overwriting a hook it didn't write itself, and never touches `git config`. It also refuses by default (`SharedHooksDirError`) if the repo's hooks directory resolves to something *shared across every repo on the machine* (a `core.hooksPath` override, not specific to this repo) -- installing there would turn this one repo's validation contract into a commit gate for every repo sharing that directory. Pass `allow_shared_hooks_dir=True` to the Python `install()` function directly to opt into that anyway. This whole feature is optional and off by default; `deliver`'s own Section 6 step above is the actual enforcement regardless of whether a hook is installed.

## Push through confirmed, safe cleanup (Section 9)

This is the part `finishing-a-development-branch` stops short of by design. Once that skill's Option 2 has pushed and opened the PR, and the task's authorized endpoint extends past "stop at the PR":

1. Watch CI with one background `gh pr checks <N> --watch` (it exits when every check has finished), then read the final state. Not a hand-written polling loop: a host guardrail that cannot resolve a loop denies it. Pending/missing/cancelled/empty is not green.
2. On red: diagnose the actual failure (read the real CI log, don't guess from the job name), fix it, **re-run the local validation contract on the fixed tree**, then push the fix. Bound repair attempts -- report an infrastructure/credential/permission blocker rather than looping on it. Never disable a test, weaken a check, or use a skip-CI marker to manufacture green.
3. Once every required check and applicable review/merge requirement is satisfied for the current PR revision (not an earlier one), and the task's authorization covers merging, merge by the **first route that applies** (prefer squash where the repo permits it; never an administrator bypass):
   - **First, if the PR is behind its base** (`gh pr view <N> --json mergeStateStatus` reads `BEHIND`; a repo that requires branches to be up to date will not merge it, and a personal-account repo has no merge queue to update it for you): bring it up to date with `gh pr update-branch <N>` (a merge of the base into the PR branch; no force push). That is a new head: watch CI on it again (step 1), and from here on the **tested sha** is that new head, never the one before the update. Update your local branch to it too (`git pull --ff-only` in the task worktree) so the cleanup check below compares the right commit. If the update conflicts, resolve it as an ordinary repair push (step 2), with the local validation contract re-run. If the host gates `gh pr update-branch`, hand it over the same way as route c below, as its own line.
   - **Repository-authorized Guardrail (preferred when enabled):** inspect `guardrail delivery status`. From the primary checkout outside the task worktree, run `guardrail delivery finish --pr <N> --head <full-tested-head-SHA> --worktree <absolute-task-worktree>`, omitting `--worktree` if none belongs to the task. The bounded executor revalidates current GitHub requirements and operator policy, performs an exact-head merge, confirms it, and cleans proven redundant task resources. Its successful result completes steps 3 and 4; verify rather than deleting twice. A failed condition is an exception: preserve resources, report it and use the operator handoff when needed. Never try another agent-executed route to evade a bounded-executor rejection. The routes below remain for environments without configured bounded delivery, following their existing authorization mechanisms.
   - **a. Auto-merge** -- the repo allows it (`gh api repos/<owner>/<repo> --jq .allow_auto_merge`) and the host lets you run it: `gh pr merge <N> --auto --squash --match-head-commit <tested sha>`. GitHub then merges only when its required checks and branch rules pass, so the agent never decides the PR is green.
   - **b. Direct merge** -- the host lets you run `gh pr merge <N> --squash --match-head-commit <tested sha>` yourself.
   - **c. The host gates the merge** -- a deny such as guardrail's `host-auto-ask-escalated` (an auto/bypass-mode host would answer guardrail's ask itself, so guardrail denies instead), or a permission prompt you may not answer for the operator. Do not retry the call, reword it, or reach for `--admin`: the gate is the point. Hand the operator **one line** instead. Before handing it over, verify each of: every required check green for the current head, the PR reports mergeable, the task worktree has no uncommitted, untracked or ignored changes, and the local branch is at the tested head. Then give, with absolute paths:

     ```
     gh pr merge <N> --squash --match-head-commit <sha> && git -C <repo> worktree remove <worktree> && git -C <repo> branch -D <branch>
     ```

     `&&` means nothing is deleted unless the merge succeeded; `--match-head-commit` means only the tested commit can merge. In Claude Code the operator types it as `! <line>`, which runs it as them inside the session and returns its output to you; on other hosts, in their terminal. If any of the four checks fails, hand over the merge part alone and report cleanup as blocked, with the reason.

   Auto-merge being enabled, or merge-queue entry, is not a confirmed merge -- keep task resources until you've actually confirmed it landed (`gh pr view <N> --json state,mergedAt,mergeCommit`, not an assumption from a green check run). A queued auto-merge waits, without a word, if another merge leaves the PR `BEHIND` its base: check `mergeStateStatus` while waiting, and if it reads `BEHIND`, update the branch as above. Don't assume the queued auto-merge survives the new head (it was queued with `--match-head-commit` naming the old one): check `gh pr view <N> --json autoMergeRequest`, and if it is gone, queue it again for the new head once its CI is green.
4. After confirmed merge: a successful bounded executor already completed task cleanup. On `merged / cleanup blocked`, retain the task endpoint and resources and resume cleanup only after resolving the named condition; never re-merge. Its strict ancestry/exact-squash-tree proof is authority where configured; patch-id alone is never authority. For legacy routes, confirm the merge commit carries the tested change (`git diff <tested sha> <merge commit>` is empty when the base did not move; otherwise it shows only what came from the base), then clean up only this task's own branch/worktree, from outside the worktree. After route c, the operator's line already did that -- confirm it (`git worktree list`, `git branch --list <branch>`). After route a or b, do it yourself if the host allows it, or hand the cleanup part of the line over the same way. The remote branch is GitHub's to delete when the repo has `delete_branch_on_merge` (`gh api repos/<owner>/<repo> --jq .delete_branch_on_merge`); otherwise `git push origin --delete <branch>`. Remove a worktree only after confirming nothing valuable is uncommitted there. Never force-delete on an ancestry mismatch without showing what's at stake and asking, mirroring `finishing-a-development-branch`'s own refusal-then-ask pattern for a non-empty worktree.
5. Report one of: **blocked**, **PR open**, **auto-merge queued**, **merge handed to operator**, **merge pending**, **merged / cleanup blocked**, or **complete** -- with the actual commands/results, the tested revision, the PR reference, the CI evidence for the final revision, confirmed-merge evidence, and cleanup results or exactly what was preserved and why. For **merge handed to operator**, include the exact line handed over and what was verified before it.

If Standards/Spec review is part of this task's policy, invoke `mp-code-review` (#7) before this section's merge step -- `deliver` does not run a second, competing review.

## Invocation and enforcement

See `references/cross-harness.md` for the illustrative entry points, the resume/finish contract, and -- separated explicitly -- what each harness is confirmed, live, to actually enforce versus what `deliver`'s own prose merely instructs (#24; all four harnesses now live-confirmed, with real gaps found for Antigravity and OpenCode's unconfigured default). Saying "deliver issue #123" for an approved implementation task selects its end-to-end endpoint. Gate 2 verifies existing authorization and readiness; it does not demand an approval already supplied. Guardrail's machine-owned repository permission remains a separate enforcement requirement.

## What this skill does not do

- Does not reimplement brainstorming, planning, TDD, debugging, or branch-finishing logic that `superpowers:*` already owns -- see `references/compatibility-map.md` for the exact handoff.
- Does not adopt `setup-matt-pocock-skills` or Matt Pocock's tracker conventions, even partially -- follows whatever tracker/spec convention the repo already demonstrates, the same fallback chain `mp-code-review` (#7) uses.
- Does not run a second, competing code review -- coordinates with `mp-code-review` (#7) instead.
- Keeps delivery authority scoped to the authorized task and endpoint; an issue alone authorizes no implementation, and a green optional check is not a required one.
- Does not provision containers, rehearse via `act`, or provision OS/desktop test infrastructure -- see `references/containers-act-os-profiles.md` for the decision and `#23` for the deferred research.
- Does not claim cross-harness enforcement parity from installation alone -- confirmed live, not assumed, that it genuinely doesn't exist (Codex: real OS-level discovery enforcement if configured; OpenCode: none by default; Antigravity: no comprehensive equivalent on its headless CLI) -- see `references/cross-harness.md` and `#24`.
