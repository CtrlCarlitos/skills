"""Self-sufficient issue/MR reference detection and fetch command
construction, replacing upstream's dependency on a tracker doc that only
exists if `setup-matt-pocock-skills` was run (it isn't, in this repo's
distribution -- see vendor/mp-code-review/DISPOSITION.md). Detects
whether the repo's remote is GitHub or GitLab, extracts issue/MR
references from commit messages, and builds the right `gh`/`glab`
command to fetch each one -- no tracker-doc dependency at all.
"""
import re
import subprocess
from pathlib import Path

ISSUE_RE = re.compile(r"(?<!\w)#(\d+)")
MERGE_REQUEST_RE = re.compile(r"(?<!\w)!(\d+)")


def detect_remote_host(repo_root: Path, run=subprocess.run) -> str | None:
    # `git config --get`, not `git remote get-url`: the latter applies
    # any `url.<base>.insteadOf` rewrite from the user's gitconfig (a
    # common multi-account SSH-alias setup, confirmed live in this very
    # environment -- e.g. https://github.com/X/ rewritten to
    # git@github-X:) and the rewritten host no longer contains
    # "github.com" at all. `git config --get` returns the raw stored URL.
    result = run(
        ["git", "config", "--get", "remote.origin.url"], cwd=repo_root, capture_output=True, text=True
    )
    if result.returncode != 0:
        return None

    url = result.stdout.strip().lower()
    if "github.com" in url:
        return "github"
    if "gitlab.com" in url:
        return "gitlab"
    return None


def extract_issue_refs(messages: list[str]) -> list[dict]:
    seen = set()
    refs = []
    for message in messages:
        for match in ISSUE_RE.finditer(message):
            ref = ("issue", int(match.group(1)))
            if ref not in seen:
                seen.add(ref)
                refs.append({"kind": "issue", "number": ref[1]})
        for match in MERGE_REQUEST_RE.finditer(message):
            ref = ("merge_request", int(match.group(1)))
            if ref not in seen:
                seen.add(ref)
                refs.append({"kind": "merge_request", "number": ref[1]})
    return refs


def fetch_commands_for(host: str | None, ref: dict) -> list[list[str]]:
    number = str(ref["number"])
    if host == "github":
        if ref["kind"] == "issue":
            # GitHub shares one numbering space between issues and PRs --
            # the ref could be either, so try issue first (the more likely
            # case for a spec reference), then fall back to pr.
            return [["gh", "issue", "view", number], ["gh", "pr", "view", number]]
        return []
    if host == "gitlab":
        if ref["kind"] == "issue":
            return [["glab", "issue", "view", number]]
        return [["glab", "mr", "view", number]]
    return []
