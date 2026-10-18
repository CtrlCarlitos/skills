---
name: repo-policy
description: Audit a GitHub repository's settings, branch protection, release-tag protection, and governance files (CODEOWNERS, CONTRIBUTING.md, SECURITY.md, PR/issue templates, Dependabot, AGENTS.md) against a configurable policy, report the gaps as a Markdown matrix, and apply only the specific changes the user explicitly approves. Use this whenever the user asks about repository settings, branch protection rules, merge strategy, required reviews, repo policy or governance compliance, standardizing a repo's configuration, or auditing GitHub repository settings -- even if they don't use the words "policy" or "audit".
---

Audit a GitHub repository against a configurable policy, report the differences, and apply only what's explicitly approved. Read-only by default. Never applies anything without itemized approval -- there is no "apply everything" path anywhere in this skill.

## Workflow

### 1. Inspect (always read-only)

```bash
python3 scripts/audit.py <owner> <repo> --repo-root <path to the local checkout>
```

This never mutates anything -- it only calls `gh api` GET endpoints and reads files. It prints which policy source is in effect, then the Markdown matrix. Show the matrix to the user verbatim; it's the deliverable for "check our repo settings," not something to paraphrase or summarize away.

A row's Current/Target can be `N/A` on both sides for a "required where applicable" setting (currently Dependabot and AGENTS.md) that doesn't apply to this repo -- that's not a gap, and the matrix says so explicitly rather than faking a match.

### 2. Propose

For each row where Action isn't `None` or `Exception: ...`, say in one line what applying it would actually do — e.g. "Add rule → create a branch ruleset requiring PRs, 1 approval, and resolved review threads on `main`." Ground this in the actual target policy values, not a generic description.

### 3. Get itemized approval

Ask which specific rows to apply. **Never offer or accept "apply everything."** A branch-protection or repo-settings change goes straight through the GitHub API — it isn't a reviewable PR diff the way a file change is — so each one needs its own explicit go-ahead. If the user says "all of it," read back the specific rows and ask them to confirm by name; don't treat the blanket phrase alone as sufficient approval.

### 4. Apply only the approved rows

Three different mechanisms, by category — use the one that matches:

- **Repo settings** (merge strategy, delete-branch-on-merge): `scripts/apply.py`'s `apply_repo_settings(owner, repo, {<only the approved keys>})`. PATCHes the repo directly; only send the keys that were actually approved.
- **Branch protection, release-tag protection** (PR requirement, review threads, signed commits, linear history, force-push/deletion blocking, required status checks): build the ruleset body from the *target* policy with `build_branch_ruleset_body(policy)` (pass `branch_pattern="~DEFAULT_BRANCH"` for branches; for tags, build a `target: "tag"` ruleset with a `ref_name` pattern like `refs/tags/v*` — see `references/writing-a-policy.md`), then `apply_branch_ruleset(owner, repo, body)`. This creates a repo-level ruleset; it never touches org-level rulesets.
- **Governance files** (CODEOWNERS, CONTRIBUTING.md, SECURITY.md, PR/issue templates, Dependabot config, AGENTS.md): these are ordinary file changes. Create them on a branch and open a PR — never commit directly to the default branch. This is the one category where "apply" means "propose a reviewable diff," because a file change is naturally PR-reviewable and a direct settings/ruleset API call is not.

### 5. Verify

Re-run `scripts/audit.py`. Confirm the rows that were just applied now show `None`. Report the before/after explicitly — "was X, now Y" — not just "done."

## Policy

A policy is a YAML file; `references/default-policy.yaml` is the built-in default and the template for writing your own. Lookup order (first match wins): the repo's own `.repo-policy/policy.yaml` → the user's `~/.config/repo-policy/policies/<name>.yaml` → the built-in default. See `references/writing-a-policy.md` for the exceptions mechanism (documented, justified deviations reported as `Exception: <reason>`, never silently dropped and never a plain unresolved gap) and the "required where applicable" settings.

The full list of settings this skill audits, their report labels, and what action each one's gap is reported with, lives in `scripts/settings.py`'s `SETTINGS` registry — that's the authoritative source, not this file.

## What this skill does not do

- Never applies a change the user didn't explicitly name. "Audit my repo" means read-only, always; applying anything is always a separate, itemized request.
- Never bypasses required reviews, branch protections, or merge checks to "fix" something faster, even if asked to as a shortcut.
- Does not manage org-level rulesets, GitHub Apps, repository visibility, or billing/plan settings — repo-level policy only.
- Does not support GitLab, Bitbucket, or other forges. Every setting in scope here is a GitHub-specific concept (rulesets, CODEOWNERS, Dependabot); this skill is GitHub-only by design, not by omission.
