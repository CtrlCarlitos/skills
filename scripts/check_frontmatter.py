#!/usr/bin/env python3
"""Fail on any skills/*/SKILL.md whose YAML frontmatter will not parse.

The `skills` CLI skips a SKILL.md whose frontmatter does not parse and still
exits 0 for the whole `add` (SKILLS_SKILL_SKIPPED in its output), so the old
grep for `^name: `/`^description: ` lines let study-coach ship uninstallable
(2026-11-13: an unquoted description containing `entry points: "..."`). This
checker parses the frontmatter the way the CLI does, requires `name` and
`description` to be non-empty strings, and requires `name` to equal the skill
folder - the folder is where the CLI installs and what `-s <name>` selects.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


class FrontmatterError(RuntimeError):
    """A SKILL.md whose frontmatter cannot be used by the skills CLI."""


def check_skill_md(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise FrontmatterError(f"{path}: no --- frontmatter block at the top")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        first = str(exc).splitlines()[0]
        raise FrontmatterError(
            f"{path}: frontmatter does not parse as YAML: {first}"
        ) from exc
    if not isinstance(data, dict):
        raise FrontmatterError(f"{path}: frontmatter is not a mapping")
    for key in ("name", "description"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise FrontmatterError(f"{path}: '{key}' must be a non-empty string")
    if data["name"] != path.parent.name:
        raise FrontmatterError(
            f"{path}: name {data['name']!r} does not match its folder "
            f"{path.parent.name!r}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        default=["skills"],
        help="skill folder roots to check (default: skills)",
    )
    args = parser.parse_args(argv)
    checked = 0
    failures = 0
    for root in args.roots:
        for path in sorted(Path(root).glob("*/SKILL.md")):
            checked += 1
            try:
                check_skill_md(path)
            except FrontmatterError as exc:
                failures += 1
                print(f"FAIL: {exc}")
    if checked == 0:
        print("FAIL: no SKILL.md found under the given roots")
        return 1
    if failures:
        print(f"{failures} of {checked} SKILL.md files failed")
        return 1
    print(f"PASS: {checked} SKILL.md frontmatter blocks parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
