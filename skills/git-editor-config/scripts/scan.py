"""Gathers raw, judgment-free facts about a repo's tracked files: git's own
mode bits (via `ls-files -s -z`), whether the file starts with a shebang,
and a binary-content signal (a null byte in the first chunk of the file).
No classification happens here -- that's classify.py's job.

Uses `-z` (NUL-separated, unquoted paths) rather than plain `ls-files -s`,
which quotes any path containing non-ASCII bytes (e.g. `"caf\\303\\251.sh"`
instead of `café.sh`) and would otherwise point this module at a path that
doesn't exist on disk. Decodes the subprocess output as UTF-8 explicitly
(not `text=True`'s own locale-default decoding, which on a non-UTF-8
Windows locale can silently mangle the non-ASCII bytes git actually
outputs, pointing this module at a path that doesn't exist either --
caught by the same except clause below, but for the wrong reason).

Submodule gitlinks (mode 160000) and symlinks (mode 120000) are reported
with no content signal -- a gitlink's "file" may not exist on disk at all
(an uninitialized submodule), and Python's file I/O follows a symlink to
whatever it points at, which can be a directory. Neither is meaningful
content to sniff for shebang/binary purposes. A tracked path missing from
the working tree (deleted without being committed, or pruned by a sparse
checkout) gets the same no-signal treatment rather than crashing.
"""
import subprocess
from pathlib import Path

_SNIFF_BYTES = 8000
_NO_CONTENT_MODES = {"160000", "120000"}


def _is_binary(chunk: bytes) -> bool:
    return b"\x00" in chunk


def scan_tracked_files(repo_root: Path, run=subprocess.run) -> list[dict]:
    result = run(
        ["git", "ls-files", "-s", "-z"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    files = []
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode = meta.split()[0]

        has_shebang = False
        is_binary = False
        if mode not in _NO_CONTENT_MODES:
            try:
                chunk = (Path(repo_root) / path).read_bytes()[:_SNIFF_BYTES]
            except (FileNotFoundError, IsADirectoryError):
                chunk = b""
            has_shebang = chunk[:2] == b"#!"
            is_binary = _is_binary(chunk)

        files.append({
            "path": path,
            "mode": mode,
            "has_shebang": has_shebang,
            "is_binary": is_binary,
        })

    return files
