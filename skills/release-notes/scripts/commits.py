"""Gather commits in a range and mechanically classify them: merge, revert
(matched to what it reverts), squash-merge PR reference. Pure parsing of
real git log output -- deciding what *section* a change belongs in (Added,
Breaking, Security, ...) is the agent's job per SKILL.md, not this
module's; this only handles what's unambiguous and mechanical.
"""
import re
import subprocess
from pathlib import Path

_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"

REVERT_TRAILER_RE = re.compile(r"This reverts commit ([0-9a-f]{7,40})\.", re.IGNORECASE)
PR_REFERENCE_RE = re.compile(r"\(#(\d+)\)\s*$")


def list_commits(repo_root: Path, base: str, head: str = "HEAD", run=subprocess.run) -> list[dict]:
    """One dict per commit in base..head, oldest first: sha, parents (list
    of parent shas; len > 1 means a merge commit), subject, body.
    """
    fmt = f"%H{_FIELD_SEP}%P{_FIELD_SEP}%s{_FIELD_SEP}%b{_RECORD_SEP}"
    result = run(
        ["git", "log", f"{base}..{head}", f"--format={fmt}", "--reverse"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    commits = []
    for record in result.stdout.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        sha, parents, subject, body = record.split(_FIELD_SEP)
        parent_shas = parents.split()
        commits.append({
            "sha": sha,
            "parents": parent_shas,
            "subject": subject,
            "body": body,
            "is_merge": len(parent_shas) > 1,
        })
    return commits


def _shas_match(a: str, b: str) -> bool:
    """git's revert trailer SHA length isn't guaranteed to match the
    length list_commits happened to request; compare by prefix either way."""
    return a == b or a.startswith(b) or b.startswith(a)


def _find_by_sha(commits: list[dict], sha: str) -> dict | None:
    return next((c for c in commits if _shas_match(c["sha"], sha)), None)


def collapse_reverted_pairs(commits: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (kept, not_included). A revert commit is excluded, along
    with the commit it reverts, only when BOTH are present in this same
    `commits` list. A revert commit whose original lies outside the range
    (a prior release's change, reverted later) is a real, visible change
    in *this* range and stays in `kept` -- only pairs fully contained in
    `commits` get collapsed.
    """
    excluded_shas: set[str] = set()
    not_included: list[dict] = []

    for commit in commits:
        match = REVERT_TRAILER_RE.search(commit["body"])
        if not match:
            continue
        original = _find_by_sha(commits, match.group(1))
        if original is None:
            continue  # reverts something outside this range -- not a pair to collapse
        not_included.append(commit)
        not_included.append(original)
        excluded_shas.add(commit["sha"])
        excluded_shas.add(original["sha"])

    kept = [c for c in commits if c["sha"] not in excluded_shas]
    return kept, not_included


def extract_pr_reference(commit: dict) -> int | None:
    """GitHub's default squash-merge commit subject ends with "(#123)"."""
    match = PR_REFERENCE_RE.search(commit["subject"])
    return int(match.group(1)) if match else None
