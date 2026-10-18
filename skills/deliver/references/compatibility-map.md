# Compatibility map: Superpowers, Matt Pocock skills, and `deliver`

Checked 2026-10-18 against Superpowers 7.0.0 (installed, `.claude/plugins/cache/superpowers-marketplace/superpowers/7.0.0/`) and `mattpocock/skills` (inspected live for #7). `deliver` is a thin coordinating layer: it invokes these skills at the right points and adds only what's genuinely missing between them. It is not a competing planning/TDD/debugging methodology.

## What already exists, and where it hands off

| Responsibility | Owned by | What `deliver` does with it |
|---|---|---|
| Read-only investigation, research, option comparison | `superpowers:brainstorming` | Invoke at task entry. `deliver` enforces the read-only boundary around it (Section 1) -- brainstorming's own description doesn't promise no side effects, so `deliver` is the thing actually responsible for that guarantee. |
| Authoring an implementation plan from an approved spec | `superpowers:writing-plans` | Invoke once Gate 1 lands on "needs a plan." Its own scope check already splits multi-subsystem specs -- `deliver` doesn't duplicate that. |
| Inline TDD execution of an approved plan | `superpowers:executing-plans` (or `subagent-driven-development` if the user prefers fresh-context-per-task) | Invoke after Gate 2. `deliver` does not reimplement task execution, red-green cycles, or ledgering -- that's this skill's job end to end. |
| The TDD red-green-refactor loop itself | `superpowers:test-driven-development` | Already the enforcement mechanism inside `executing-plans`; `deliver` references it, doesn't restate it. |
| Branch/worktree isolation | `superpowers:using-git-worktrees` | Invoke when Gate 2 authorizes implementation and no task-owned workspace exists yet. Detects and reuses an already-isolated session per its own Step 0 -- `deliver` relies on that, doesn't re-detect it. |
| Evidence-before-claims discipline | `superpowers:verification-before-completion` | `deliver`'s local-validation contract (Section 6 below) is what *defines* the commands that evidence must come from; `verification-before-completion` is the rule that you may not claim success without running them. Two different layers -- one says what to run, the other says you must actually run it. |
| Merge-locally / push+PR / keep-as-is, and worktree cleanup *for those three paths* | `superpowers:finishing-a-development-branch` | **This is the skill `deliver` extends, not replaces.** Confirmed by reading it directly: its own Option 2 ("Push and Create PR") stops once the PR exists -- "Keep the worktree — your human partner iterates on PR feedback there." It has no path for diagnosing/fixing red CI, squash-merging once authorized, confirming the merge landed, or cleaning up *after* merge. `deliver` picks up exactly at that point when the task's authorization extends past "open a PR." |
| PR review (Standards/Spec) | `mp-code-review` (#7) | `deliver` never runs a second, competing review. If Standards/Spec review is wanted before the pre-push gate or before merge, invoke `mp-code-review` explicitly; `deliver`'s own pre-push gate is about *local validation* (lint/test/build), not code review. |
| PR body formatting | Matt Pocock's `pr` skill (narrow template, already installed via dotfiles) | Optional, cosmetic; `deliver` doesn't require it and doesn't duplicate its template. |
| Post-mortem / retro | Matt Pocock's `retro` skill | Out of scope for `deliver` entirely -- that's a separate lifecycle event, not part of delivering one task. |
| Repo-tracker setup, triage labels, domain-doc layout | `setup-matt-pocock-skills` | **Explicitly not adopted**, per the issue's own instruction and the #7 precedent (that skill isn't installed in this repo's distribution; telling a user to run it is the exact bug #7 fixed in `mp-code-review`). `deliver` follows whatever tracker/spec convention the repository already demonstrates (commit-message issue refs, a `docs/`/`specs/`/`.scratch/` file, or asking), the same fallback chain `mp-code-review`'s step 2 already uses. |

## The genuine gap `deliver` fills

Nothing above, individually or in combination, covers: **push → diagnose and fix red CI → re-run the exact local validation that CI runs → repeat until green → squash-merge once authorized → confirm the merge landed → clean up safely.** `finishing-a-development-branch`'s menu is the closest existing thing and stops one step short (at "PR created"), by design -- it assumes a human continues from there. `deliver` is for the case where the task's authorization already covers that continuation, so the agent doesn't have to ask the same "what now" question after every push, the way this project's own session history shows happening by hand, every time, via an explicit "fix on red, merge on green, cleanup on merged" instruction.

The other genuinely new piece is the **local-validation contract** (`scripts/validation_contract.py`): a repo-owned mapping from what CI actually runs to the exact local command, built by parsing the repository's own `.github/workflows/*.yml` rather than hand-maintaining a second list that drifts from CI. Nothing in Superpowers or Matt's skills does this; `verification-before-completion` requires evidence but never says *which commands* constitute it for a given repo.

## Avoiding duplicate/conflicting triggers

- `deliver` never calls a research/brainstorming skill and then assumes its output is automatically write-authorized -- Gate 1 is the explicit checkpoint between "brainstorming produced a recommendation" and "something gets written," including a specification or tracker record.
- `deliver` does not re-run TDD logic itself; it hands off to `executing-plans`/`test-driven-development` and only re-enters once that skill reports task completion, at the pre-push gate.
- `deliver` does not call `finishing-a-development-branch` AND implement its own merge-locally/push+PR menu -- it calls that skill for the menu, and only adds behavior for the "push + PR, then continue through CI/merge/cleanup" path when authorization covers it, which `finishing-a-development-branch` doesn't claim to handle.
- Both `deliver` and `mp-code-review` can appear in one task (PR review, then CI), and neither assumes the other ran -- `deliver`'s pre-push gate and `mp-code-review`'s Standards/Spec review check genuinely different things (local validation vs. code quality against a spec).
