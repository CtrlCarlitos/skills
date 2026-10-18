"""Resolve a release-notes commit range and sanity-check the repo state
before anything else runs. Per the issue: "Range first... print the
resolved range before writing anything. If no tag exists, the history is
shallow, or the directory is not the repo, say so and stop."
"""
import subprocess
from pathlib import Path


class RangeError(Exception):
    """The message is exactly what the skill should tell the user, then stop."""


def _git(args: list[str], repo_root: Path, run) -> str:
    result = run(["git", *args], cwd=repo_root, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def resolve_range(
    repo_root: Path,
    base: str | None = None,
    head: str = "HEAD",
    run=subprocess.run,
) -> dict:
    _, code, _ = _git(["rev-parse", "--is-inside-work-tree"], repo_root, run)
    if code != 0:
        raise RangeError(f"{repo_root} is not a git repository.")

    is_shallow, _, _ = _git(["rev-parse", "--is-shallow-repository"], repo_root, run)
    if is_shallow == "true":
        raise RangeError(
            f"{repo_root} is a shallow clone; the full history is needed to resolve a release range. "
            "Fetch full history first (e.g. `git fetch --unshallow`)."
        )

    if base is None:
        base, code, stderr = _git(["describe", "--tags", "--abbrev=0", head], repo_root, run)
        if code != 0:
            raise RangeError(
                f"No tag found reachable from {head}, and no --base was given. "
                "Specify an explicit base commit/tag, or create a tag to describe the range from."
            )

    head_sha, code, stderr = _git(["rev-parse", head], repo_root, run)
    if code != 0:
        raise RangeError(f"Could not resolve {head!r} to a commit: {stderr}")

    return {"base": base, "head": head, "head_sha": head_sha}
