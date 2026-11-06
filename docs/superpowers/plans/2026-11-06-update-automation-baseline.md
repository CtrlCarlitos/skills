# Update Automation Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add monthly GitHub Actions updates and review-only vendored-upstream drift monitoring to `CtrlCarlitos/skills`.

**Architecture:** Dependabot owns only GitHub Actions update pull requests. A standard-library Python checker treats each `UPSTREAM` file as data and compares GitHub content-object SHAs for the vendored subtree at the pin and upstream default branch; a read-only scheduled workflow reports drift but never changes repository content.

**Tech Stack:** Dependabot v2 configuration, GitHub Actions, Python 3 standard library (`argparse`, `json`, `pathlib`, `urllib`), `unittest`, GitHub REST API.

**Spec:** `docs/superpowers/specs/2026-11-06-update-automation-baseline.md`

## Global Constraints

- Configure only the `github-actions` Dependabot ecosystem; do not add pip automation.
- Group all Action updates monthly and allow at most one open update pull request.
- Never auto-merge an update.
- Vendored-upstream monitoring is read-only and must never edit pins, rebuild vendors, open pull requests, or create issues.
- Parse `UPSTREAM` as four literal `key=value` records (`repo`, `path`, `commit`, `date`); never source it as shell.
- Use only the Python standard library and read-only `GITHUB_TOKEN` permissions.

## Review Focus

- A default-branch commit outside the configured subtree must report unchanged; covered by Task 2's equal-tree-SHA test.
- A changed configured subtree must identify the vendor and return exit code 1; covered by Task 2's stale-result and CLI tests.
- Missing or duplicate metadata keys must fail closed before any request; covered by Task 2's parser tests.
- A deleted upstream path or API rate-limit/network failure must return exit code 2, not appear unchanged; covered by Task 2's API error test.
- Scheduled automation must have read-only repository permissions and no mutation triggers; covered by Task 3's workflow contract test.

---

## File Structure

- Create `.github/dependabot.yml` for monthly grouped GitHub Actions pull requests.
- Create `scripts/check_vendor_updates.py` for metadata parsing, GitHub API reads, subtree comparison, text/summary output, and CLI exit codes.
- Create `scripts/tests/test_check_vendor_updates.py` for offline unit and CLI tests with mocked API responses.
- Modify `.github/workflows/ci.yml` to run the new checker tests on Ubuntu.
- Create `.github/workflows/vendor-upstream-check.yml` for the monthly/manual read-only drift check.

### Task 1: GitHub Actions Dependabot

**Files:**
- Create: `.github/dependabot.yml`

**Interfaces:**
- Consumes: GitHub's Dependabot v2 schema.
- Produces: One grouped monthly `github-actions` update queue rooted at `/`.

- [ ] **Step 1: Create the Dependabot configuration**

Set `version: 2`; ecosystem `github-actions`; directory `/`; schedule interval `monthly`, time `09:00`, timezone `Etc/UTC`; group `github-actions` with pattern `*`; `open-pull-requests-limit: 1`; and commit-message prefix `ci`.

- [ ] **Step 2: Validate the configuration contract**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

text = Path('.github/dependabot.yml').read_text(encoding='utf-8')
assert text.count('package-ecosystem:') == 1
assert 'package-ecosystem: github-actions' in text
assert 'interval: monthly' in text
assert 'open-pull-requests-limit: 1' in text
assert 'package-ecosystem: pip' not in text
PY
```

Expected: exit 0 with no output.

- [ ] **Step 3: Commit**

```bash
git add .github/dependabot.yml
git commit -m "ci: add monthly Actions updates"
```

### Task 2: Vendored Subtree Drift Checker

**Files:**
- Create: `scripts/check_vendor_updates.py`
- Create: `scripts/tests/test_check_vendor_updates.py`
- Modify: `.github/workflows/ci.yml:17-58`

**Interfaces:**
- Produces: `Upstream(repo: str, path: str, commit: str, date: str)` and `CheckResult(name: str, pinned_sha: str, current_sha: str, default_branch: str)` immutable records.
- Produces: `parse_upstream(path: pathlib.Path) -> Upstream`; rejects unknown, missing, duplicate, or empty keys and a `commit` that is not 40 lowercase hexadecimal characters.
- Produces: `github_json(url: str, token: str) -> dict`; sends GitHub JSON accept headers, bearer authentication, and a fixed user agent, and raises a checker-specific error for HTTP, network, JSON, or shape failures.
- Produces: `check_vendor(name: str, vendor_root: pathlib.Path, token: str, fetch=github_json) -> CheckResult`; reads repository metadata for `default_branch`, then content metadata for the configured path at the pin and default branch, comparing each response's `sha`.
- Produces: `main(argv: list[str] | None = None) -> int`; checks explicit vendor names or all immediate `vendor/*/UPSTREAM` parents, prints one result per vendor, writes `GITHUB_STEP_SUMMARY` when set, and returns 0 unchanged, 1 stale, or 2 metadata/API error.

- [ ] **Step 1: Write failing parser and comparison tests**

Add `unittest` cases named `test_parse_upstream_accepts_literal_fields`, `test_parse_upstream_rejects_duplicate_or_unknown_fields`, `test_parse_upstream_rejects_invalid_commit`, `test_equal_subtree_sha_is_unchanged_even_when_default_branch_advanced`, `test_different_subtree_sha_is_stale`, `test_missing_path_or_api_error_fails_closed`, and `test_main_returns_one_and_names_stale_vendor`. Use temporary directories and an injected fake `fetch`; make no network calls.

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `python3 -m unittest discover -s scripts/tests -p 'test_check_vendor_updates.py' -v`

Expected: FAIL because `scripts/check_vendor_updates.py` does not exist.

- [ ] **Step 3: Implement the checker**

Use `urllib.parse.quote(path, safe='/')` and `urllib.parse.urlencode({'ref': ref})` for content URLs. Treat the content response's `sha` as the subtree identity. Catch checker errors per vendor so all vendors are reported, but return 2 if any error occurred; otherwise return 1 if any subtree differs.

- [ ] **Step 4: Run the checker tests**

Run: `python3 -m unittest discover -s scripts/tests -p 'test_check_vendor_updates.py' -v`

Expected: all new tests pass with no network access.

- [ ] **Step 5: Add the checker test command to Ubuntu CI**

Add a named step to `.github/workflows/ci.yml` after the metadata check and before dependency installation. Run the exact unittest discovery command from Step 4; do not add it to Windows or macOS because the production workflow runs on Ubuntu and the behavior is platform-independent.

- [ ] **Step 6: Run local regression tests**

Run: `python3 -m unittest discover -s scripts/tests -p 'test_check_vendor_updates.py' -v && bash scripts/tests/test_sync_vendor.sh`

Expected: all Python tests pass; shell test prints both `PASS` lines.

- [ ] **Step 7: Commit**

```bash
git add scripts/check_vendor_updates.py scripts/tests/test_check_vendor_updates.py .github/workflows/ci.yml
git commit -m "ci: detect vendored upstream drift"
```

### Task 3: Monthly Read-Only Workflow

**Files:**
- Create: `.github/workflows/vendor-upstream-check.yml`
- Modify: `scripts/tests/test_check_vendor_updates.py`

**Interfaces:**
- Consumes: `scripts/check_vendor_updates.py` from Task 2 and the workflow-provided `GITHUB_TOKEN`.
- Produces: A `workflow_dispatch` and `17 9 1 * *` scheduled job named `check` on `ubuntu-latest`.

- [ ] **Step 1: Write a failing workflow contract test**

Add `test_workflow_is_monthly_manual_and_read_only` asserting the workflow has only `schedule` and `workflow_dispatch` triggers, cron `17 9 1 * *`, top-level `permissions: contents: read`, one `ubuntu-latest` job, a full 40-character SHA pin for `actions/checkout`, and a run step `python3 scripts/check_vendor_updates.py` with `GH_TOKEN: ${{ github.token }}`.

- [ ] **Step 2: Run the workflow contract test and verify it fails**

Run: `python3 -m unittest scripts.tests.test_check_vendor_updates.VendorUpdateWorkflowTests -v`

Expected: FAIL because `.github/workflows/vendor-upstream-check.yml` does not exist.

- [ ] **Step 3: Create the scheduled workflow**

Pin checkout as `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7`. Do not request `issues`, `pull-requests`, `actions`, or write permissions, and do not use a third-party action.

- [ ] **Step 4: Run all repository tests**

Run: `python3 -m unittest discover -s scripts/tests -v && bash scripts/tests/test_sync_vendor.sh`

Expected: all tests pass. Then run the existing skill test commands from `.github/workflows/ci.yml` in the available local environment; record any platform-only omissions rather than weakening CI.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/vendor-upstream-check.yml scripts/tests/test_check_vendor_updates.py
git commit -m "ci: schedule vendor update checks"
```

### Task 4: Passive Repository Security Setting

**Files:**
- No repository files.

**Interfaces:**
- Produces: GitHub dependency vulnerability alerts enabled; automated security fixes remain disabled.

- [ ] **Step 1: Enable vulnerability alerts after the code pull request merges**

Run: `gh api --method PUT repos/CtrlCarlitos/skills/vulnerability-alerts`

Expected: HTTP 204.

- [ ] **Step 2: Verify passive-only settings**

Run: `gh api -i repos/CtrlCarlitos/skills/vulnerability-alerts` and `gh api repos/CtrlCarlitos/skills/automated-security-fixes`

Expected: vulnerability-alert request returns HTTP 204; automated security fixes report `enabled: false`.

- [ ] **Step 3: Verify the merged workflows**

Manually dispatch `Vendor Upstream Check`, wait for completion, and confirm its summary names `skill-creator`, `show-me`, and `mp-code-review`. Confirm the workflow did not create a branch, issue, or pull request.
