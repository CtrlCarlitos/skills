"""Policy lookup chain: repo override -> named user policy -> built-in
default. Same convention as this repo's release-notes/update-docs design
(repo-committed override beats a personal cross-repo default, which beats
the skill's shipped default).
"""
from pathlib import Path

import yaml


def load_policy(
    repo_root: Path,
    home: Path,
    builtin_policy: dict,
    policy_name: str = "default",
) -> tuple[dict, str]:
    """Returns (policy_dict, human-readable source description)."""
    repo_override = repo_root / ".repo-policy" / "policy.yaml"
    if repo_override.is_file():
        return (
            yaml.safe_load(repo_override.read_text(encoding="utf-8")),
            f"repo override: {repo_override}",
        )

    user_policy = home / ".config" / "repo-policy" / "policies" / f"{policy_name}.yaml"
    if user_policy.is_file():
        return (
            yaml.safe_load(user_policy.read_text(encoding="utf-8")),
            f"user policy: {user_policy}",
        )

    return builtin_policy, "built-in default"
