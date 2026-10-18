# mp-code-review fork: provenance and findings

Fork for CtrlCarlitos/skills#7. Checked 2026-10-18 against
`mattpocock/skills` (upstream pin: `3da8c01116264675eeefbd6e9d59c734de9095cc`,
2026-10-07, confirmed via the GitHub API as the latest commit touching
`skills/engineering/code-review` as of this check).

## Why fork, not just rename

Dotfiles already renames upstream's `code-review` to `mp-code-review`
when staging it (`scripts/lib/agent-skills.sh`), avoiding a naming
collision with Claude Code's built-in code review and Superpowers'
`receiving-code-review`. That rename only patches the `name:` frontmatter
field — the skill's actual content still says, verbatim:

> The issue tracker should have been provided to you. If not, tell the
> user to run `/setup-matt-pocock-skills`.

`setup-matt-pocock-skills` is explicitly out of scope for dotfiles (see
dotfiles#269), and it's the skill that would have written the tracker
doc step 2's fallback chain also depends on ("fetched via the workflow
in the tracker doc"). Telling a user to run a skill that was never
installed, and silently depending on a config file that was never
written, are real bugs — a rename can't fix either, only owning the
content can.

## What changed from upstream

One patch, `patches/0001-drop-tracker-dependency-and-rename.patch`:

- Removed the `/setup-matt-pocock-skills` line entirely.
- Rewrote step 2's item 1 to be self-sufficient: `scripts/tracker.py`
  detects the repo's remote (GitHub vs GitLab), extracts issue/MR
  references from commit messages (`#123`, `Closes #45`, GitLab `!67`),
  and returns the `gh`/`glab` command(s) to fetch each one, in order. No
  tracker-doc dependency anywhere in the chain now.
- Renamed the skill to `mp-code-review` in the frontmatter `name:`
  field itself (not just the installed directory, which is what
  dotfiles' rename-on-stage did) — the actual fix for the naming
  collision this fork exists partly to resolve.
- Added `LICENSE.txt` (MIT, Matt Pocock © 2026, exact upstream text),
  `scripts/tracker.py`, and `tests/test_tracker.py`, matching the
  `skill-creator`/`show-me` forks' convention.
- `agents/openai.yaml` is preserved verbatim from upstream — unlike
  `show-me`'s, it carries no invocation-suppression policy (this skill
  is meant to be triggerable, not manual-only), so there was nothing to
  decide here.

## What this fork does not change

Per the issue's explicit non-goals: the Standards/Spec two-axis review
mechanism (steps 1, 3, 4, 5, and the "Why two axes" section) is
**untouched**. Confirmed by the patch diff itself: every hunk in
`patches/0001-...patch` falls inside the removed tracker line or step
2's rewritten item 1 — nothing in steps 1, 3, 4, 5 or the closing section
appears in the diff at all. No adoption of `setup-matt-pocock-skills` or
Matt's tracker/process workflow, even partially; no new tracker
integration is written, only detection of what's already there (a
GitHub/GitLab remote) and direct use of the CLI the user already has.

## Eval: baseline vs. candidate on the exact scenario being fixed

Two fresh subagents, each given only one version of `SKILL.md` (no
context from this fork's development) and the same task -- "Review the
changes since v1.0.0" against a real git repo with a commit message
containing `(#7)` -- instructed to follow the skill literally through
step 2 ("Identify the spec source") and report what happened.

**Baseline (pristine upstream `SKILL.md`):** Got genuinely stuck, exactly
as predicted. Checked the repo for a tracker doc, `CONTRIBUTING.md`,
`docs/`, `specs/`, `.scratch/` -- none exist. Correctly refused to invent
a workflow the skill doesn't specify (it noticed the repo's real git
remote but said using it "would be inventing a workflow the skill
doesn't specify, not following it" -- a faithful literal reading). Ended
at: *"Per the skill's own setup note, since the issue tracker wasn't
provided, I should ask you to run `/setup-matt-pocock-skills` -- but
that command isn't registered as an available skill or slash command in
my environment, so I can't actually point you to something that
works."* This is the exact bug the issue describes, reproduced live, not
asserted from reading the prose.

**Candidate (patched `SKILL.md`):** Used `scripts/tracker.py` for real:
`detect_remote_host` → `"github"`, `extract_issue_refs` on the commit
message → `[{"kind": "issue", "number": 7}]`, `fetch_commands_for` →
`[["gh", "issue", "view", "7"], ["gh", "pr", "view", "7"]]`. Confirmed
`gh` installed and authenticated, ran `gh issue view 7` for real
(exit 0, didn't need the `pr view` fallback), and used its real output
as the spec source. Never mentioned `/setup-matt-pocock-skills` or any
unavailable command.

**A real finding from the candidate run, not fixed here:** the fixture
repo's remote happened to point at this *actual* `CtrlCarlitos/skills`
repo, so `gh issue view 7` fetched the real issue #7 -- which is this
very fork's own tracking issue, unrelated to the fixture's fictitious
`calc.py` diff. The candidate agent flagged this correctly: step 2 (in
both upstream and this fork) has no check that a fetched issue's content
actually relates to the diff being reviewed; a coincidental or wrong
issue number would silently become "the spec." This is a pre-existing
upstream characteristic, not something this patch introduces or
worsens, and fixing it would mean adding relevance-validation logic to
step 2 -- out of scope per the issue's own non-goal ("No rewrite of the
Standards/Spec two-axis review mechanism"). Noted here as an honest
caveat, not corrected.

## Findings from building and testing `scripts/tracker.py`

- **A real `git config` vs. `git remote get-url` gap, confirmed live in
  this very environment.** This repo's own global gitconfig has
  `url.<alias>.insteadOf` rules rewriting `https://github.com/<org>/` to
  a per-account SSH alias (a common multi-account setup). `git remote
  get-url origin` returns the *rewritten* URL — no `github.com` substring
  left in it at all — while `git config --get remote.origin.url` returns
  the raw stored value. `detect_remote_host` uses the latter specifically
  because of this; a regression test reproduces the exact rewrite rule
  found in this environment's gitconfig.
- **`gh issue view <N>` on a GitHub PR number doesn't fail.** Tested live
  against this repo's own PR #21: `gh issue view 21` succeeds and returns
  sensible data, because GitHub's Issues API returns pull requests too
  (PRs are a superset of issues in GitHub's data model). The
  issue-then-pr fallback order in `fetch_commands_for` is therefore
  mostly a documentation nicety for a human reading the two attempts, not
  a strict necessity — but it's kept, since the `gh pr view` fallback
  still matters for GitLab-style setups ported over, and the pure
  function remains correct and tested either way.

## Follow-up (not filed here)

A separate dotfiles issue, coordinated the same way dotfiles#269
coordinated with skills#1 for `show-me`: switch dotfiles' `mp-code-review`
install source from `mattpocock/skills` to `CtrlCarlitos/skills`, once
this fork is validated. Not blocking; filed once this side is ready, per
the issue's own acceptance criteria.
