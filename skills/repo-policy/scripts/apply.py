"""Itemized apply layer. Every function here is called explicitly for one
policy area, with the exact subset of changes the user approved -- there is
no "apply everything" entry point anywhere in this skill. See SKILL.md for
why: a GitHub ruleset/settings PATCH isn't reviewable the way a file change
in a PR is, so approval has to be itemized here instead.
"""
import json
import subprocess


def build_branch_ruleset_body(policy: dict, branch_pattern: str = "~DEFAULT_BRANCH") -> dict:
    """Pure: turns a target policy dict into the body for
    POST /repos/{owner}/{repo}/rulesets (target: branch). No network access.
    """
    rules = []

    if policy.get("require_pull_request"):
        rules.append({
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": policy.get("required_approving_review_count", 0),
                "require_code_owner_review": bool(policy.get("require_code_owner_review")),
                "required_review_thread_resolution": bool(policy.get("required_review_thread_resolution")),
                "dismiss_stale_reviews_on_push": False,
                "require_last_push_approval": False,
                "allowed_merge_methods": ["merge", "squash", "rebase"],
            },
        })

    if policy.get("required_status_checks"):
        rules.append({
            "type": "required_status_checks",
            "parameters": {
                "required_status_checks": [{"context": c} for c in policy["required_status_checks"]],
                "strict_required_status_checks_policy": True,
            },
        })

    for key, rule_type in (
        ("required_signatures", "required_signatures"),
        ("required_linear_history", "required_linear_history"),
        ("block_force_push", "non_fast_forward"),
        ("block_branch_deletion", "deletion"),
    ):
        if policy.get(key):
            rules.append({"type": rule_type})

    return {
        "name": "repo-policy: branch protection",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": [branch_pattern], "exclude": []}},
        "rules": rules,
    }


def apply_repo_settings(owner: str, repo: str, changes: dict, run=subprocess.run) -> None:
    """changes: the subset of {merge_strategy, delete_branch_on_merge} the
    user approved -- only those fields are sent. Making no call at all when
    `changes` is empty is deliberate: this is never invoked as a catch-all.
    """
    body = {}
    if "delete_branch_on_merge" in changes:
        body["delete_branch_on_merge"] = changes["delete_branch_on_merge"]
    if "merge_strategy" in changes:
        strategy = changes["merge_strategy"]
        body["allow_squash_merge"] = strategy in ("squash_only", "any")
        body["allow_merge_commit"] = strategy in ("merge_only", "any")
        body["allow_rebase_merge"] = strategy in ("rebase_only", "any")

    if not body:
        return

    run(
        ["gh", "api", "-X", "PATCH", f"repos/{owner}/{repo}", "--input", "-"],
        input=json.dumps(body),
        capture_output=True,
        text=True,
        check=True,
    )


def apply_branch_ruleset(owner: str, repo: str, ruleset_body: dict, run=subprocess.run) -> None:
    run(
        ["gh", "api", "-X", "POST", f"repos/{owner}/{repo}/rulesets", "--input", "-"],
        input=json.dumps(ruleset_body),
        capture_output=True,
        text=True,
        check=True,
    )
