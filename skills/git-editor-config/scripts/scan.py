"""Gathers raw, judgment-free facts about a repo's tracked files: git's own
mode bits (via `ls-files -s`), whether the file starts with a shebang, and a
binary-content signal (a null byte in the first chunk of the file). No
classification happens here -- that's classify.py's job.
"""
import subprocess
from pathlib import Path

_SNIFF_BYTES = 8000


def _is_binary(chunk: bytes) -> bool:
    return b"\x00" in chunk


def scan_tracked_files(repo_root: Path, run=subprocess.run) -> list[dict]:
    result = run(
        ["git", "ls-files", "-s"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    files = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode = meta.split()[0]

        chunk = (Path(repo_root) / path).read_bytes()[:_SNIFF_BYTES]
        has_shebang = chunk[:2] == b"#!"
        is_binary = _is_binary(chunk)

        files.append({
            "path": path,
            "mode": mode,
            "has_shebang": has_shebang,
            "is_binary": is_binary,
        })

    return files
