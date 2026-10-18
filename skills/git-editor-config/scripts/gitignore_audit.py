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
        gaps.append({"path": file["path"], "reason": result["reason"]})
    return gaps


def find_unignored_generated_files(repo_root: Path, run=subprocess.run) -> list[dict]:
    result = run(
        ["git", "status", "--porcelain", "--ignored=no", "--", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    gaps = []
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        path = line[3:]
        chunk = (Path(repo_root) / path).read_bytes()[:_SNIFF_BYTES]
        if _is_binary(chunk):
            gaps.append({"path": path})

    return gaps
