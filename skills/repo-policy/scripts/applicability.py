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


# Copies of other projects' manifests, not this repo's dependencies. A
# manifest under one of these is skipped.
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".claude", ".tox", "dist", "build"}


def has_a_dependency_manifest(repo_root: Path) -> bool:
    """True when Dependabot has something to update here: a recognized
    manifest anywhere in the repo (CtrlCarlitos/skills keeps its
    requirements.txt per skill, none at the root), or GitHub Actions
    workflows (its github-actions ecosystem).
    """
    workflows = repo_root / ".github" / "workflows"
    if workflows.is_dir() and any(workflows.iterdir()):
        return True
    for name in DEPENDENCY_MANIFESTS:
        for path in repo_root.rglob(name):
            if not IGNORED_DIRS.intersection(path.relative_to(repo_root).parts[:-1]):
                return True
    return False


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
