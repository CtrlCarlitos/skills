"""Detect what kind of project a repo is, and resolve the update-docs type
guide for it through the same lookup chain release-notes/scripts/repo_type.py
uses (itself mirroring repo-policy's policy.py): repo override -> user
config -> built-in default.

"course" and "docs" types have no file-system signature to detect -- they
are only ever reached by an explicit type_name (repo override or user
config), never by detect_type.
"""
from pathlib import Path


def detect_type(repo_root: Path) -> str:
    if (repo_root / "__manifest__.py").is_file():
        return "odoo"

    if (repo_root / "go.mod").is_file():
        return "go"

    pubspec = repo_root / "pubspec.yaml"
    if pubspec.is_file() and "flutter" in pubspec.read_text(encoding="utf-8"):
        return "flutter"

    mix_exs = repo_root / "mix.exs"
    if mix_exs.is_file() and ":phoenix" in mix_exs.read_text(encoding="utf-8"):
        return "phoenix"

    return "generic"


def resolve_type_guide(
    repo_root: Path,
    home: Path,
    builtin_dir: Path,
    type_name: str | None = None,
) -> tuple[str, str]:
    """Returns (guide_markdown_text, human-readable source description)."""
    repo_override = repo_root / ".update-docs" / "type.md"
    if repo_override.is_file():
        return repo_override.read_text(encoding="utf-8"), f"repo override: {repo_override}"

    if type_name is None:
        type_name = detect_type(repo_root)

    user_guide = home / ".config" / "update-docs" / "types" / f"{type_name}.md"
    if user_guide.is_file():
        return user_guide.read_text(encoding="utf-8"), f"user config: {user_guide}"

    builtin_guide = builtin_dir / f"{type_name}.md"
    if builtin_guide.is_file():
        return builtin_guide.read_text(encoding="utf-8"), "built-in default"

    raise FileNotFoundError(
        f"No type guide found for {type_name!r}: no repo override, no user config at "
        f"{user_guide}, and no built-in guide at {builtin_guide}."
    )
