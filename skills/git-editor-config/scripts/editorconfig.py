"""Parses an existing .editorconfig into pattern/settings sections and
finds file extensions present in the repo with no matching section.
Reuses gitattributes.py's pattern_matches rather than reimplementing glob
matching -- .editorconfig section headers use the same glob style.
"""
import re
from pathlib import Path

from scripts.gitattributes import pattern_matches

_SECTION_HEADER = re.compile(r"^\[(.+)\]$")


def parse_editorconfig(content: str) -> list[dict]:
    sections = []
    current = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        header = _SECTION_HEADER.match(line)
        if header:
            current = {"pattern": header.group(1), "settings": {}}
            sections.append(current)
            continue

        if current is not None and "=" in line:
            key, _, value = line.partition("=")
            current["settings"][key.strip()] = value.strip()

    return sections


def build_editorconfig_gaps(files: list[dict], existing_sections: list[dict]) -> list[dict]:
    seen_extensions = {}
    for file in files:
        extension = Path(file["path"]).suffix
        if extension and extension not in seen_extensions:
            seen_extensions[extension] = file["path"]

    gaps = []
    for extension, example_path in seen_extensions.items():
        covered = any(
            pattern_matches(section["pattern"], f"x{extension}")
            for section in existing_sections
        )
        if covered:
            continue
        gaps.append({"extension": extension, "example_path": example_path})

    return gaps
