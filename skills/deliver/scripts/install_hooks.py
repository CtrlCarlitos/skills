"""Install/uninstall an optional pre-commit + pre-push hook pair that
delegates to hook_runner.py (the same validation_contract.py the skill
already runs inline). Never touches git config -- writes/removes plain
files in the repo's existing hooks directory, resolved via `git
rev-parse --git-path hooks` so it works identically from any linked
worktree (hooks are shared across all of a repo's worktrees, not
per-worktree). Never overwrites a hook file it didn't write itself --
every hook this tool writes carries MARKER as its first content line
after the shebang, and both install and uninstall check for it first.
"""
import subprocess
from pathlib import Path

MARKER = "# installed-by: deliver-skill (CtrlCarlitos/skills#23) -- remove with install_hooks.uninstall"

_HOOK_NAMES = ("pre-commit", "pre-push")


class HookConflictError(Exception):
    pass


def hooks_dir(repo_root: Path, run=subprocess.run) -> Path:
    result = run(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else Path(repo_root) / path


def _is_ours(path: Path) -> bool:
    return path.exists() and MARKER in path.read_text(encoding="utf-8")


def _hook_script(deliver_root: Path, repo_root: Path) -> str:
    runner = Path(deliver_root) / "scripts" / "hook_runner.py"
    return (
        "#!/bin/sh\n"
        f"{MARKER}\n"
        "if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi\n"
        f'"$PY" "{runner}" "{Path(repo_root)}"\n'
        "exit $?\n"
    )


def install(repo_root: Path, deliver_root: Path, run=subprocess.run) -> list[str]:
    target_dir = hooks_dir(repo_root, run)

    for name in _HOOK_NAMES:
        path = target_dir / name
        if path.exists() and not _is_ours(path):
            raise HookConflictError(f"{path} already exists and wasn't installed by this tool -- refusing to overwrite it")

    target_dir.mkdir(parents=True, exist_ok=True)
    script = _hook_script(deliver_root, repo_root)
    for name in _HOOK_NAMES:
        path = target_dir / name
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)

    return list(_HOOK_NAMES)


def uninstall(repo_root: Path, run=subprocess.run) -> list[str]:
    target_dir = hooks_dir(repo_root, run)

    removed = []
    for name in _HOOK_NAMES:
        path = target_dir / name
        if _is_ours(path):
            path.unlink()
            removed.append(name)

    return removed
