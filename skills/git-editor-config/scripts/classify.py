"""Suggests a .gitattributes rule for one scanned file, from its raw
signal alone (scan.py's output shape). Never guesses: a file with no clear
signal returns None rather than a default rule, so the audit never
proposes a boilerplate line for content it hasn't actually inspected.
"""
from pathlib import Path

_PATCH_EXTENSIONS = (".patch", ".diff")


def classify_file(file: dict) -> dict | None:
    suffix = Path(file["path"]).suffix

    if suffix in _PATCH_EXTENSIONS:
        return {
            "attrs": ["text", "eol=lf", "-diff"],
            "reason": "patch/diff file: must stay LF for `git apply` against an upstream tree, and must not be diffed",
        }

    if file["is_binary"]:
        return {
            "attrs": ["-text", "-diff"],
            "reason": "binary content detected (null byte in file)",
        }

    if file["has_shebang"]:
        return {
            "attrs": ["text", "eol=lf"],
            "reason": "shebang line: must stay LF or the interpreter line breaks on checkout",
        }

    return None
