"""Gathers the current repo state via `gh api` subprocess calls.

Each function builds one command and parses its JSON. `run` is injected
(ordinarily subprocess.run) so callers can fake it in tests -- this module
is never exercised against live GitHub by the test suite.
"""
import json
import subprocess
from pathlib import Path

from scripts.settings import merge_strategy_from_flags


def _gh_api(path: str, run):
    result = run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def inspect_repo_settings(owner: str, repo: str, run=subprocess.run) -> dict:
    data = _gh_api(f"repos/{owner}/{repo}", run)
    return {
        "default_branch": data.get("default_branch"),
        "merge_strategy": merge_strategy_from_flags(data),
        "delete_branch_on_merge": bool(data.get("delete_branch_on_merge")),
    }


def inspect_branch_rules(owner: str, repo: str, branch: str, run=subprocess.run) -> dict:
    """Uses the effective-rules endpoint (merges classic branch protection
    and any applicable rulesets, org- or repo-level) rather than the classic
    protection endpoint, so this reflects the real current state regardless
    of which mechanism set it.
    """
    rules = _gh_api(f"repos/{owner}/{repo}/rules/branches/{branch}", run)
    by_type = {rule["type"]: rule for rule in rules}
    pr_params = by_type.get("pull_request", {}).get("parameters", {})
    status_checks_params = by_type.get("required_status_checks", {}).get("parameters", {})

    return {
        "require_pull_request": "pull_request" in by_type,
        "required_approving_review_count": pr_params.get("required_approving_review_count", 0),
        "require_code_owner_review": bool(pr_params.get("require_code_owner_review")),
        "required_review_thread_resolution": bool(pr_params.get("required_review_thread_resolution")),
        "required_signatures": "required_signatures" in by_type,
        "required_linear_history": "required_linear_history" in by_type,
        "block_force_push": "non_fast_forward" in by_type,
        "block_branch_deletion": "deletion" in by_type,
        "required_status_checks": [c["context"] for c in status_checks_params.get("required_status_checks", [])],
    }


def inspect_tag_protection(owner: str, repo: str, run=subprocess.run) -> dict:
    """There's no effective-rules endpoint for tags the way there is for
    branches, so this lists rulesets directly and checks for any active
    one targeting tags. Good enough for a yes/no "is anything protecting
    release tags" signal; doesn't need each ruleset's full rule detail.
    """
    rulesets = _gh_api(f"repos/{owner}/{repo}/rulesets", run)
    protected = any(
        ruleset.get("target") == "tag" and ruleset.get("enforcement") == "active"
        for ruleset in rulesets
    )
    return {"release_tags_protected": protected}


def inspect_files(repo_root: Path, file_map: dict[str, list[str]]) -> dict:
    """file_map: policy key -> candidate relative paths; present if any one
    of them exists (e.g. CODEOWNERS can live at the root or under .github/).
    """
    return {
        key: any((repo_root / candidate).exists() for candidate in candidates)
        for key, candidates in file_map.items()
    }
