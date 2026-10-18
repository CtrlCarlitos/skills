---
name: release-notes
description: Draft release notes or a changelog section for an explicit commit range (a tag, a commit, or "since the last release"). Use this whenever the user asks to write, draft, or update release notes, a CHANGELOG, or "what's new" for a range of commits -- never as an automatic step after other work, and never to pick a version, tag, or publish anything.
---

Draft release notes for an explicit commit range, grounded in the actual commits and their diffs, not commit-message labels. Draft only, on demand -- never an automatic follow-up to other work, and never a step that tags, pushes, publishes, or picks a version on its own.

## Workflow

### 1. Gather the grounded facts

```bash
python3 -m scripts.gather <repo-root> [--base <tag-or-commit>] [--head <commit>] [--type <type-name>]
```

Run from this skill's directory (`skills/release-notes/`). This is read-only and prints JSON: the resolved range, the commits in it (with fully-contained revert pairs already collapsed out and excluded, and GitHub squash-merge PR numbers already extracted), the repo-type guide to apply, and whether an existing changelog file was found and whether it's machine-generated.

**If this raises an error, stop and show the user the message verbatim** — it means no tag exists, the clone is shallow, `--base`/`--head` don't resolve, or the directory isn't the repo. Don't guess a range to work around it.

When `--base` is omitted, the range is `<previous tag>..HEAD` via `git describe`. Print the resolved range to the user before doing anything else — "Range: `v1.2.0..HEAD` (14 commits)" — so they can object before you draft anything.

A date-window summary ("what changed since Monday") is allowed when the user asks for it, but label it as activity, not a release, and don't force it into the Keep a Changelog shape below.

### 2. Build grounded entries

For each commit in `commits` (already revert-collapsed):

- **Read the diff**, not just the subject, for any commit labeled `refactor`, `test`, `chore`, or similarly "internal." A commit type never hides a change — if the diff shows a changed default, a removed public API, a migration, or a security fix, it goes in the right section regardless of its label.
- **Collapse squash merges**: GitHub's default squash-merge subject already ends in `(#123)` (`pr_reference` is already extracted) — write one entry per PR, not per raw commit, when a PR's commits were squashed.
- **Attribute real commits only.** No metrics, benefits, test results, or security claims the commit/diff/PR doesn't support. If the commit message makes a claim ("2x faster"), mark it as the author's claim, not a verified fact, or verify it before stating it as one.
- **Keep confidential detail out.** A security fix gets a user-facing entry about *impact and remediation* ("users must X"), never exploit detail, internal ticket names, or anything not meant for the public changelog.
- **List `not_included`** (the collapsed revert pairs, and anything unmerged you know didn't ship) under the "Not included" section with why.
- **End every entry with its references**: `(#123, abc1234)` — the PR number when there is one, and the short commit SHA, so every claim is checkable.

### 3. Apply the repo type

`repo_type.guide` (from step 1's JSON) is the loaded guide for this repo's type — read it for what counts as breaking, security-relevant, or an upgrade note *here specifically*, beyond the generic rules. The seven built-in guides are in `references/`; `references/writing-a-type.md` explains the lookup chain (repo `.release-notes/type.md` → `~/.config/release-notes/types/<name>.md` → built-in) and how to write a custom one.

### 4. Render the section

Use `scripts/render.py`'s `render_release_section(version, date, sections, range_text=..., commit_count=..., pr_count=..., audience=...)` to lay the entries out. Section order is fixed: Breaking changes, then the six Keep a Changelog sections (Added, Changed, Deprecated, Removed, Fixed, Security), then Upgrade notes, then Not included — a section with nothing in it is omitted automatically.

`version` and `audience` come from the user. If they didn't give them, use `"Unreleased"` for the version and ask for the audience (`users`, `operators`, `developers`, or `learners`) rather than guessing — the breaking/security framing in step 2 depends on who's reading.

**If the repo already has its own changelog format** (not this skill's default), match that format instead — read a couple of its existing entries first. The default format below only applies when there's nothing to match.

### 5. Show the draft; file only if asked

By default, show the rendered section in the conversation. Only write it into a file when the user explicitly asks to update the changelog:

- `scripts/changelog_file.py`'s `find_changelog(repo_root)` locates the existing file (checked already in step 1's JSON too); `is_generated(content)` tells you if it's machine-generated — if so, **stop and say so instead of editing it**, the same way you would for any other generated file.
- `insert_section_at_top(existing_content, new_section)` inserts the new section above the first existing `##`-level entry, leaving everything else untouched. If there's no changelog file yet, it creates one with a `# Changelog` title.

Never pick a version number, create a git tag, create a GitHub release, push, or publish anything — this skill's output is always a draft a human (or another skill) acts on.

### 6. Lint before handing it back

```python
from scripts.lint import lint_file
lint_file(path, config_path=".markdownlint-cli2.jsonc")
```

Uses an installed `markdownlint-cli2` if present, falls back to `npx markdownlint-cli2` if Node is available, and otherwise skips the check and says so — never a hard dependency, never a hard failure for its own absence. A result with `passed: False` means fix the Markdown and re-lint, not ignore it. A repo's own markdownlint config always wins over the one this skill ships.

### 7. Docs to check (hand-off, not a fix)

End the draft with a short, read-only list of documentation that might now be stale: "`--foo` was renamed in `abc1234`; `README.md` still mentions `--foo`." Name the change, the file, and the stale text for each item. This skill never edits docs — it's a hand-off to a docs-maintenance skill or to a person. Omit the section entirely when nothing turned up; don't pad it.

## Default format

Keep a Changelog (keepachangelog.com), checked with `markdownlint-cli2`. No emoji. Newest release first. Empty sections omitted.

```markdown
## [<version> | Unreleased] - <YYYY-MM-DD>

Range: `<base>..<head>` (<N> commits, <M> PRs). Audience: <users | operators | developers | learners>.

### Breaking changes
- <what changed and what the reader must do> (#123, abc1234)

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
### Upgrade notes
### Not included
```

## What this skill does not do

- Never runs on its own after other work — only when explicitly asked.
- Never picks a version, creates a tag or GitHub release, pushes, or publishes.
- Never edits a changelog file unless the user explicitly asked for the file to be updated, and never a changelog file that identifies itself as machine-generated.
- Never invents a metric, benefit, test result, or security claim the commits don't support.
- Never edits documentation — the "docs to check" list in step 7 is a hand-off, not a fix.
- Does not install, fork, or depend on the upstream `changelog-generator` skill this was inspired by; it's an original implementation addressing that skill's gaps (no range resolution, commit-label trust, invented metrics, no revert/squash handling, no references, assumed audience/brand voice).
