# deliver: finish a PR when the host gates the merge

Status: approved by the operator 2026-11-16 (approach A, in conversation).

## Why

guardrail v0.23.43 (agent-guardrails #559) turns every ask on an auto or bypass host into a deny
(`host-auto-ask-escalated`). On a lab VM (CtrlCarlitos/dotfiles#430) that denied, in order:

- `gh pr merge`;
- `git worktree remove` and `git branch -D`;
- a CI polling loop.

Those are exactly `deliver` Section 9's steps 1, 3 and 4. The skill already says a host may block
an action and must not be worked around (`references/cross-harness.md`), but it does not say what to
do instead, so agents improvise. The operator's goal: coding agents that work autonomously, in a
safe way.

## Goals

- **One handoff per PR when the host gates the merge:** a single line the operator types (in Claude
  Code, `! <line>`) that merges and then cleans up. The agent checks everything it can before handing
  it over and confirms everything after.
- **No handoff at all when the merge is safe for the agent to run:** where the repo allows
  auto-merge and the host permits `gh pr merge --auto` (agent-guardrails #606), the agent runs it
  and GitHub's required checks decide.
- **CI watching that works under guardrail:** one background `gh pr checks <N> --watch`, no loop.

## Non-goals

- Changing isolation. Worktrees stay `superpowers:using-git-worktrees`' job
  (`compatibility-map.md`).
- Changing guardrail; that is agent-guardrails #605 and #606.
- Changing any merge authority rule. Gate 2 still decides whether the task covers a merge.

## Anti-goals

- **No workaround of a deny:** no retries, no rewording a gated command to slip past the hook, no
  `--admin`.
- **No unconditional cleanup:** the handed-over line must not delete anything if the merge fails, and
  must not be offered while the worktree is dirty or its branch is not at the tested head.

## Approaches

- **A (chosen): one combined handoff, worktrees kept, `--auto` when allowed.** It has the fewest
  operator actions, and it becomes zero once #606 lands.
- **B: separate merge and cleanup handoffs.** It is closest to today's "confirm, then clean up"
  order, but costs two operator actions per PR and stays manual for cleanup.
- **C: wait for #606.** Agents keep hitting denies meanwhile.

## Design

Section 9 of `SKILL.md`:

1. **Watch CI with one background `gh pr checks <N> --watch`.** Pending, missing, cancelled or empty
   is still not green, as today.
2. Red CI: unchanged.
3. **Merge, by the first route that applies:**
   - **a. Auto-merge:** the repo allows auto-merge and the host permits it, so run
     `gh pr merge <N> --auto --squash --match-head-commit <tested sha>`. A queued auto-merge is not
     a confirmed merge (as today).
   - **b. Direct merge:** the host permits a direct merge, so run it as today.
   - **c. The host gates the merge** (a deny such as `host-auto-ask-escalated`, or a permission prompt
     the agent may not answer itself). Do not retry. Before handing over, verify:
     - every required check is green for the current head;
     - the PR reports mergeable;
     - the worktree has no uncommitted or untracked changes;
     - the local branch is at the tested head.

     Then hand over one line, built from absolute paths:

     ```
     gh pr merge <N> --squash --match-head-commit <sha> && git -C <repo> worktree remove <wt> && git -C <repo> branch -D <branch>
     ```

     `&&` means nothing is deleted unless the merge succeeded. `--match-head-commit` means it merges
     only the tested commit. When a check fails, hand over the merge alone and report cleanup as
     blocked, with the reason.
4. **After the operator runs it (or the auto-merge lands):**
   - confirm the merge with `gh pr view --json state,mergedAt,mergeCommit`;
   - confirm the squash commit carries the tested change (`git diff <tested sha> <merge commit>` is
     empty when the base did not move);
   - confirm the worktree and branch are gone.

   The remote branch is GitHub's to delete when the repo has `delete_branch_on_merge`; otherwise
   delete it, or hand that over the same way.
5. **Report states:** add **merge handed to operator** (pending their command) and **auto-merge
   queued**.

`references/cross-harness.md`, "Separating workflow selection from merge authority": the
paragraph saying not to work around a host block gains the handoff as what to do instead, and a
note that guardrail v0.23.43 escalates asks in auto mode.

`evals/evals.json` gains three `documented-not-yet-run` cases:

- `host-gated-merge-handoff`;
- `handoff-refused-when-dirty`;
- `auto-merge-when-host-allows`.

## Left to the builder

- Exact wording, following the file's existing voice.
- Whether to mention Claude Code's `!` by name: yes, as the example, with other hosts' terminal as
  the general case.
