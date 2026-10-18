"""Discover documentation files in a repo, respecting Rule 6 ("hands off
other records"): a CHANGELOG (release-notes' territory) or an accepted ADR
is never surfaced as a doc to audit in the first place, not just protected
from editing later.
"""
import re
import subprocess
from pathlib import Path

CHANGELOG_NAME_RE = re.compile(r"(^|/)(CHANGELOG|HISTORY|NEWS)(\.[^/]+)?$", re.IGNORECASE)
RECORD_DIR_RE = re.compile(r"(^|/)(adr|decisions)(/|$)", re.IGNORECASE)

DOC_EXTENSIONS = (".md", ".rst", ".adoc")
DOC_BASENAME_RE = re.compile(r"(^|/)readme$", re.IGNORECASE)


def is_excluded_record(path: str) -> bool:
    return bool(CHANGELOG_NAME_RE.search(path) or RECORD_DIR_RE.search(path))


def is_doc_path(path: str) -> bool:
    if is_excluded_record(path):
        return False

    stem, _, ext = path.rpartition(".")
    if ext and f".{ext}".lower() in DOC_EXTENSIONS:
        return True

    return bool(DOC_BASENAME_RE.search(path.rsplit("/", 1)[-1]) or path.rsplit("/", 1)[-1].upper() == "README")


def discover_doc_files(repo_root: Path, run=subprocess.run) -> list[str]:
    """Tracked files only (git ls-files), so .gitignored content and
    anything not yet committed are never mistaken for part of the repo's
    real documentation."""
    result = run(["git", "ls-files"], cwd=repo_root, capture_output=True, text=True)
    return [p for p in result.stdout.splitlines() if is_doc_path(p)]
