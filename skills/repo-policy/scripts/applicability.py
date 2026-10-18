"""'Required where applicable' detection. Currently just Dependabot: it's
only a real gap if the repo has a package manifest for Dependabot to act
on at all -- a repo with no dependencies isn't missing anything by not
having one.
"""
from pathlib import Path

DEPENDENCY_MANIFESTS = (
    "package.json",
    "go.mod",
    "requirements.txt",
    "Gemfile",
    "Cargo.toml",
    "composer.json",
    "pom.xml",
    "build.gradle",
    "pyproject.toml",
)


def has_a_dependency_manifest(repo_root: Path) -> bool:
    return any((repo_root / name).exists() for name in DEPENDENCY_MANIFESTS)


# Deliberately-authored markers only -- NOT bare ".claude" or ".cursor"
# directories. Confirmed live (via a repo-policy eval run) that a bare
# ".claude/" is not a reliable signal: Claude Code's own worktree-isolation
# feature creates ".claude/worktrees/" automatically just from being used,
# regardless of whether a repo's maintainers ever adopted any AI-agent
# tooling. Every marker here is something a human had to actually write.
AGENTIC_MARKERS = (
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/commands",
    ".cursor/rules",
    ".github/copilot-instructions.md",
)


def looks_agentic(repo_root: Path) -> bool:
    """AGENTS.md is only a real gap in a repo that's already set up for AI
    coding agents in some other way -- a plain repo with none of these
    markers isn't missing anything by not having one.
    """
    return any((repo_root / marker).exists() for marker in AGENTIC_MARKERS)
