"""Install/uninstall an optional pre-commit + pre-push hook pair that
delegates to hook_runner.py (the same validation_contract.py the skill
already runs inline). Never touches git config -- writes/removes plain
files in the repo's existing hooks directory. Never overwrites a hook
file it didn't write itself -- every hook this tool writes carries
MARKER as its second line (right after the shebang), and both install
and uninstall check for exactly that before touching anything.

The hooks directory is resolved via `git rev-parse --git-path hooks`,
which respects `core.hooksPath` if the user or some other tool has set
it. That path can be a directory SHARED by every repo on the machine,
not specific to this one -- confirmed on a real machine during this
work, where a test that wrote through that real resolution overwrote a
real, pre-existing file outside its control (see DISPOSITION.md). By
default, `install` refuses to write into a hooks directory that isn't
this specific repo's own local one (compared against
`<git-common-dir>/hooks`), because writing a repo-specific validation
hook into a directory shared by every repo on the machine would turn
one repo's CI contract into a commit gate for every repo that shares
it. `allow_shared_hooks_dir=True` opts into that anyway, explicitly.

The hook script never bakes in the repo root: it resolves it at
runtime via `git rev-parse --show-toplevel`, since git always invokes a
hook with its cwd already at the committing worktree's own top level --
baking in the repo root at install time would validate the WRONG tree
when the hooks directory is shared across a repo's worktrees (which it
always is; hooks are never per-worktree).
"""
import shlex
import subprocess
import sys
from pathlib import Path

MARKER = "# installed-by: deliver-skill (CtrlCarlitos/skills#23) -- remove with install_hooks.uninstall"

_HOOK_NAMES = ("pre-commit", "pre-push")


class HookConflictError(Exception):
    pass


class SharedHooksDirError(Exception):
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


def _repo_local_hooks_dir(repo_root: Path, run=subprocess.run) -> Path:
    result = run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    common_dir = Path(result.stdout.strip())
    if not common_dir.is_absolute():
        common_dir = Path(repo_root) / common_dir
    return (common_dir / "hooks").resolve()


def _is_shared_hooks_dir(repo_root: Path, target_dir: Path, run) -> bool:
    return target_dir.resolve() != _repo_local_hooks_dir(repo_root, run)


def _is_ours(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, PermissionError, OSError):
        return False
    return len(lines) >= 2 and lines[1] == MARKER


def _hook_script(deliver_root: Path, python_executable: str) -> str:
    runner = (Path(deliver_root).resolve() / "scripts" / "hook_runner.py").as_posix()
    py = shlex.quote(python_executable)
    runner_quoted = shlex.quote(runner)
    return (
        "#!/bin/sh\n"
        f"{MARKER}\n"
        'REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1\n'
        f'{py} {runner_quoted} "$REPO_ROOT"\n'
        "exit $?\n"
    )


def install(
    repo_root: Path,
    deliver_root: Path,
    run=subprocess.run,
    allow_shared_hooks_dir: bool = False,
    python_executable: str | None = None,
) -> list[str]:
    target_dir = hooks_dir(repo_root, run)

    if not allow_shared_hooks_dir and _is_shared_hooks_dir(repo_root, target_dir, run):
        raise SharedHooksDirError(
            f"{target_dir} is a shared/global hooks directory (core.hooksPath), not specific to this repo. "
            "Installing here would run this repo's validation contract on every commit in every repo that "
            "shares it. Pass allow_shared_hooks_dir=True to install anyway."
        )

    for name in _HOOK_NAMES:
        path = target_dir / name
        if path.exists() and not _is_ours(path):
            raise HookConflictError(f"{path} already exists and wasn't installed by this tool -- refusing to overwrite it")

    script = _hook_script(deliver_root, python_executable or sys.executable)
    target_dir.mkdir(parents=True, exist_ok=True)

    written = []
    try:
        for name in _HOOK_NAMES:
            path = target_dir / name
            path.write_text(script, encoding="utf-8")
            path.chmod(0o755)
            written.append(name)
    except OSError:
        for name in written:
            (target_dir / name).unlink(missing_ok=True)
        raise

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


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("install", "uninstall"):
        print("usage: python3 -m scripts.install_hooks install|uninstall [repo_root] [deliver_root]")
        return 1

    action = argv[0]
    repo_root = Path(argv[1]) if len(argv) > 1 else Path.cwd()

    if action == "install":
        deliver_root = Path(argv[2]) if len(argv) > 2 else Path(__file__).resolve().parent.parent
        try:
            installed = install(repo_root, deliver_root)
        except (HookConflictError, SharedHooksDirError) as exc:
            print(f"install_hooks: {exc}")
            return 1
        print(f"installed: {', '.join(installed)}")
        return 0

    removed = uninstall(repo_root)
    print(f"removed: {', '.join(removed) if removed else '(nothing to remove)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
