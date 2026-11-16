# Writing a policy

A policy is a YAML file with the same keys as `default-policy.yaml` — copy
that file to start your own. Every key is optional; a key this skill's
registry (`scripts/settings.py`) doesn't recognize is ignored, and a key
you omit simply isn't audited for that repo.

## Where a policy lives

Looked up in this order, first match wins:

1. **The repo itself**: `.repo-policy/policy.yaml` at the repo root. Commit
   this so everyone working on that repo audits against the same policy.
2. **The user**: `~/.config/repo-policy/policies/<name>.yaml`, for a
   personal policy reused across repos that don't have their own. `<name>`
   defaults to `default`; pass `--policy-name <name>` to use a different one.
3. **Built in**: `references/default-policy.yaml`, shipped with this skill.

## Repository-specific CI checks

`required_status_checks` is a list of exact check-name strings (the same
names that show up as required status checks in GitHub's branch settings
UI). Leave it empty to not audit CI check names at all — the built-in
default does this because there's no universal set of check names; a
repo's own `.repo-policy/policy.yaml` should list its actual ones.

`require_status_checks: true` is the name-independent half: it flags a
default branch with no required check at all, which the empty name list
alone never would. `strict_required_status_checks` audits GitHub's
"require branches to be up to date before merging".

## Policies for agent-driven repos

When coding agents open and merge PRs, the merge is safe only if GitHub,
not the agent, decides it. These keys are what that depends on:

- `require_status_checks: true` plus the repo's real
  `required_status_checks`: something has to pass.
- `strict_required_status_checks: true`: it has to pass against the
  current base.
- `no_bypass_actors: true`: nobody — an agent using the maintainer's token
  included — can skip the rules. The audit lists any bypass actor it finds
  under the matrix.
- `allow_auto_merge: true`: an agent can queue `gh pr merge --auto` and
  let GitHub merge once the checks pass.
- `required_approving_review_count`: GitHub counts approvals only from
  someone other than the PR's author. On a single-maintainer repo whose
  PRs (agents' included) come from the maintainer's own account, any value
  above 0 means no PR can ever merge; set 0 there and let the checks gate.

## Justified exceptions

Add an `exceptions:` block mapping a setting key to the reason it doesn't
need to match the policy right now:

```yaml
exceptions:
  required_signatures: "contributors sign via SSH keys GitHub can't verify yet"
```

A setting with a documented exception is reported as `Exception: <reason>`
in the audit matrix, not as a plain unresolved gap, and not silently
dropped from the report either.

## "Required where applicable" settings

Right now this applies to `dependabot` only: it's reported as a real gap
only when the repo has a recognized dependency manifest (`package.json`,
`go.mod`, `Cargo.toml`, etc. — see `scripts/applicability.py`). A repo with
no dependencies isn't missing anything by not having a Dependabot config.

## Setting keys this skill audits

See `scripts/settings.py`'s `SETTINGS` list for the exact keys, their
report labels, and what action each one's gap is reported with. That list
is the authoritative registry; this guide doesn't duplicate it.
