# Update Automation Baseline Design

## Goal

Add conservative dependency and vendored-upstream monitoring without allowing automation to modify or merge vendored skills.

## Dependency Updates

- Configure Dependabot for the `github-actions` ecosystem only.
- Run monthly at 09:00 UTC and group all Action updates into one pull request.
- Allow at most one open Actions update pull request.
- Do not configure pip Dependabot while `pyyaml` remains unconstrained.
- Enable GitHub dependency vulnerability alerts, but leave Dependabot security updates disabled so alerts remain passive.
- Never auto-merge dependency pull requests.

## Vendored Upstream Monitoring

- Run on the first day of each month and on manual dispatch.
- Read each `vendor/*/UPSTREAM` file as data, never by shell-sourcing it.
- For each vendor, resolve the upstream repository's default branch through the GitHub API.
- Compare the Git tree/content-object SHA for the configured `path` at the pinned `commit` with the same path on the default branch.
- Report unchanged and stale vendors in the job summary.
- Exit nonzero when any vendor is stale, metadata is malformed, the path is absent, or GitHub returns an error.
- Use only the Python standard library and the workflow-provided `GITHUB_TOKEN` with read-only contents permission.
- Do not edit `UPSTREAM`, rebuild a vendor, open a pull request, create an issue, or merge anything.

## Verification

- Unit tests cover metadata parsing, unchanged subtrees, stale subtrees, unrelated upstream changes, missing paths, and API failures.
- Existing vendor rebuild checks and all existing repository tests continue to pass.
