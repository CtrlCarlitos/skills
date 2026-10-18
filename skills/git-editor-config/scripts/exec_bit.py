"""Detects executable-bit drift from one scanned file's raw signal.

Deliberately asymmetric: flagging a missing `+x` on a shebang script is
always safe to suggest. Flagging "remove +x" is only safe for a fixed set
of extensions that are unambiguously non-executable by convention -- many
repos legitimately ship executable `.py`/`.sh` files with no shebang, so
those are never flagged for removal, to avoid false-positive churn.
"""
from pathlib import Path

NON_EXECUTABLE_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".css", ".html"}


def exec_bit_drift(file: dict) -> str | None:
    is_exec = file["mode"].endswith("755")

    if file["has_shebang"] and not is_exec:
        return "missing"

    if is_exec and not file["has_shebang"] and Path(file["path"]).suffix in NON_EXECUTABLE_EXTENSIONS:
        return "unexpected"

    return None
