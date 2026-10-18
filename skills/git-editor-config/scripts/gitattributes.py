"""Parses an existing .gitattributes file into pattern/attrs rules and
answers "is this path already covered?" -- an audit tool's coverage check,
not a drop-in replacement for git's own attribute matcher.

`pattern_matches` is an fnmatch-based approximation of git's actual
gitignore-glob semantics, not a full reimplementation. It handles a bare
pattern (matches at any depth, by basename), a `/`-containing pattern, a
leading `**/` segment (also matches at the root, not just nested), and a
single `{a,b,c}` brace alternation -- the common real-world cases this
audit actually hit. It does not handle a leading `/` anchor (meant to pin
a pattern to the repo root specifically) or a `**` segment anywhere other
than as a leading `**/`. Good enough to answer "would some existing rule
plausibly already cover this path" for audit purposes; a pattern using
one of the unhandled forms can still produce a false-negative "not
covered" gap report that a human reviewing the proposal would recognize
and decline.
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
    if "{" in pattern and "}" in pattern:
        start = pattern.index("{")
        end = pattern.index("}", start)
        alternatives = pattern[start + 1:end].split(",")
        if len(alternatives) > 1:
            prefix, suffix = pattern[:start], pattern[end + 1:]
            return any(pattern_matches(f"{prefix}{alt}{suffix}", path) for alt in alternatives)

    if pattern.startswith("**/"):
        # fnmatch treats "/" in a pattern as a literal character, so
        # "**/*.sh" (meaning "at any depth, including the root") would
        # otherwise never match a root-level path with no "/" in it at all.
        if pattern_matches(pattern[3:], path):
            return True

    if "/" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return fnmatch.fnmatch(Path(path).name, pattern)


def is_covered(path: str, rules: list[dict]) -> bool:
    return any(pattern_matches(rule["pattern"], path) for rule in rules)


def resolve_attributes(path: str, rules: list[dict]) -> dict:
    """Resolves the final value of every attribute name that applies to
    `path`, mirroring git's own per-attribute (not per-rule) resolution: a
    later matching rule overrides only the specific attribute names it
    mentions, it does not replace an earlier rule's other attributes. A
    bare name resolves to True, a `-name` to False, a `name=value` to the
    string value.
    """
    resolved = {}
    for rule in rules:
        if not pattern_matches(rule["pattern"], path):
            continue
        for attr in rule["attrs"]:
            if attr.startswith("-"):
                resolved[attr[1:]] = False
            elif "=" in attr:
                name, _, value = attr.partition("=")
                resolved[name] = value
            else:
                resolved[attr] = True
    return resolved
