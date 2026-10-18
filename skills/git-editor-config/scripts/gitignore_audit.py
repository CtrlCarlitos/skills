"""Two narrow .gitignore checks, both grounded in the repo's actual
content rather than a fetched template: tracked files that look generated
(reusing classify.py's binary signal) and untracked files that look
generated but aren't matched by any existing .gitignore pattern.
"""
import subprocess
from pathlib import Path

from scripts.classify import classify_file
from scripts.scan import _is_binary, _SNIFF_BYTES


def find_tracked_generated_files(files: list[dict]) -> list[dict]:
    gaps = []
    for file in files:
        result = classify_file(file)
        if result is None or "-text" not in result["attrs"]:
            continue
        gaps.append({
            "path": file["path"],
            "reason": f"{result['reason']} -- tracked but looks generated; after adding to .gitignore, also `git rm --cached` it",
        })
    return gaps


def find_unignored_generated_files(repo_root: Path, run=subprocess.run) -> list[dict]:
    # --untracked-files=all lists each file inside an untracked directory
    # individually, rather than collapsing it to one "?? dir/" line -- the
    # collapsed form would make the read below raise IsADirectoryError.
    result = run(
        ["git", "status", "--porcelain", "--ignored=no", "--untracked-files=all", "-z", "--", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    gaps = []
    for entry in result.stdout.split("\0"):
        if not entry.startswith("?? "):
            continue
        path = entry[3:]
        chunk = (Path(repo_root) / path).read_bytes()[:_SNIFF_BYTES]
        if _is_binary(chunk):
            gaps.append({"path": path, "reason": "untracked, looks generated (binary content) -- consider adding to .gitignore"})

    return gaps
