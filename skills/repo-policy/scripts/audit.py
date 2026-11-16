#!/usr/bin/env python3
"""Audit a repo's settings, branch protection, release-tag protection, and
governance files against a policy, and print the Markdown comparison
matrix. Read-only: makes no changes anywhere. See apply.py for making
changes -- always invoked separately, and always itemized by the caller.
"""
import argparse
import sys
from pathlib import Path

import yaml

from scripts.applicability import has_a_dependency_manifest, looks_agentic
from scripts.compare import build_matrix
from scripts.inspect import (
    inspect_branch_rules,
    inspect_bypass_actors,
    inspect_files,
    inspect_repo_settings,
    inspect_tag_protection,
)
from scripts.policy import load_policy
from scripts.report import render_markdown
from scripts.settings import SETTINGS

FILE_CANDIDATES = {
    "codeowners": ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"],
    "contributing": ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"],
    "security_md": ["SECURITY.md", ".github/SECURITY.md"],
    "pr_template": [
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/pull_request_template.md",
        "PULL_REQUEST_TEMPLATE.md",
    ],
    "issue_templates": [".github/ISSUE_TEMPLATE", ".github/ISSUE_TEMPLATE.md"],
    "dependabot": [".github/dependabot.yml", ".github/dependabot.yaml"],
    "agents_md": ["AGENTS.md"],
}


def gather_current_state(
    owner: str,
    repo: str,
    repo_root: Path,
    file_candidates: dict,
    inspect_repo_settings_fn=inspect_repo_settings,
    inspect_branch_rules_fn=inspect_branch_rules,
    inspect_tag_protection_fn=inspect_tag_protection,
    inspect_files_fn=inspect_files,
    inspect_bypass_actors_fn=inspect_bypass_actors,
) -> dict:
    current: dict = {}
    current.update(inspect_repo_settings_fn(owner, repo))
    current.update(inspect_branch_rules_fn(owner, repo, current["default_branch"]))
    current.update(inspect_bypass_actors_fn(current.pop("ruleset_refs", [])))
    # "Any required CI": a repo with no required check at all is a gap
    # whatever the policy names its checks (#42).
    current["require_status_checks"] = bool(current.get("required_status_checks"))
    current.update(inspect_tag_protection_fn(owner, repo))
    current.update(inspect_files_fn(repo_root, file_candidates))
    return current


def apply_not_applicable_overrides(current: dict, policy: dict, repo_root: Path) -> tuple[dict, dict]:
    """Normalizes a "required where applicable" setting to the same "N/A"
    sentinel on both sides when it doesn't apply here, so the matrix reports
    it as a match rather than faking "Present" -- a value of "N/A" must
    never be mistaken for the file actually existing. Returns new dicts;
    does not mutate the ones passed in.
    """
    current = dict(current)
    policy = dict(policy)
    # A Dependabot config that exists applies by definition: never hide it as N/A.
    if "dependabot" in policy and current.get("dependabot") is not True and not has_a_dependency_manifest(repo_root):
        current["dependabot"] = "N/A"
        policy["dependabot"] = "N/A"
    if "agents_md" in policy and not looks_agentic(repo_root):
        current["agents_md"] = "N/A"
        policy["agents_md"] = "N/A"
    # An empty check-name list means "don't audit the names" (writing-a-policy.md);
    # require_status_checks still flags a branch with no required check at all.
    if policy.get("required_status_checks") == []:
        del policy["required_status_checks"]
    return current, policy


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("--repo-root", default=".", help="Local checkout path, for the file-based checks")
    parser.add_argument("--policy-name", default="default")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    builtin_path = Path(__file__).resolve().parent.parent / "references" / "default-policy.yaml"
    builtin_policy = yaml.safe_load(builtin_path.read_text(encoding="utf-8"))

    policy, source = load_policy(repo_root, Path.home(), builtin_policy, policy_name=args.policy_name)
    exceptions = policy.get("exceptions", {})

    current = gather_current_state(args.owner, args.repo, repo_root, FILE_CANDIDATES)
    current, policy = apply_not_applicable_overrides(current, policy, repo_root)

    rows = build_matrix(current, policy, SETTINGS, exceptions=exceptions)

    print(f"Policy source: {source}\n")
    print(render_markdown(rows))
    if current.get("bypass_actors"):
        print("\nRuleset bypass actors (each can skip the rules on the default branch):")
        for actor in current["bypass_actors"]:
            print(f"- {actor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
