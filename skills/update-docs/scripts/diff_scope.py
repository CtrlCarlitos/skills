"""Resolve which files a diff or range touches, so the default audit mode
scopes to the change (Rule 2) instead of walking the whole repo.
"""
import subprocess
from pathlib import Path


class DiffScopeError(Exception):
    """The message is exactly what the skill should tell the user, then stop."""


def changed_files(
    repo_root: Path,
    base: str | None = None,
    head: str = "HEAD",
    run=subprocess.run,
) -> list[str]:
    """base=None means the working tree's uncommitted changes against head."""
    check = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_root, capture_output=True, text=True)
    if check.returncode != 0:
        raise DiffScopeError(f"{repo_root} is not a git repository.")

    diff_arg = head if base is None else f"{base}..{head}"
    result = run(["git", "diff", "--name-only", diff_arg], cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise DiffScopeError(f"Could not diff {diff_arg!r}: {result.stderr.strip()}")

    return [p for p in result.stdout.splitlines() if p]
