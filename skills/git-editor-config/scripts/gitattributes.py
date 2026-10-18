"""Parses an existing .gitattributes file into pattern/attrs rules and
answers "is this path already covered?" -- an audit tool's coverage check,
not a drop-in replacement for git's own attribute matcher.

`pattern_matches` is an fnmatch-based approximation of git's actual
gitignore-glob semantics: it does not handle `**` double-star segments or
git's anchoring edge cases (a leading `/`, a pattern with no `/` matching
at every directory level). Good enough to answer "would some existing rule
plausibly already cover this path" for audit purposes.
"""
import fnmatch
from pathlib import Path


def parse_gitattributes(content: str) -> list[dict]:
    rules = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *attrs = line.split()
        rules.append({"pattern": pattern, "attrs": attrs})
    return rules


def pattern_matches(pattern: str, path: str) -> bool:
    if "/" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return fnmatch.fnmatch(Path(path).name, pattern)


def is_covered(path: str, rules: list[dict]) -> bool:
    return any(pattern_matches(rule["pattern"], path) for rule in rules)
