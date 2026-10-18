"""Tests for install_hooks: install/uninstall a tiny pre-commit/pre-push
hook pair, worktree-safe, never touching a hook this tool didn't write,
and refusing a shared/global hooks directory by default.

All install/uninstall tests inject a fake `run` that answers git's two
resolution calls (`--git-path hooks` and `--git-common-dir`) with fixed,
test-owned paths -- never the real git call. This isn't a shortcut: a
machine can have `core.hooksPath` configured globally (this one does),
which makes the real call resolve to the SAME shared directory for every
repo on the machine, including a disposable tmp fixture. A test that
exercised the real resolution during a file-WRITE discovered this the
hard way, writing fixture content into a real, pre-existing file outside
any test's control.

`WorktreeAndIsolationTests` is the one place real git runs, and every
real git subprocess it starts (`git init`, `git commit`, `git worktree
add`) is given `GIT_CONFIG_GLOBAL=os.devnull` and `GIT_CONFIG_NOSYSTEM=1`
in its environment, so none of it can read or trigger this machine's
real global hooks or config -- belt-and-suspenders on top of the
production SharedHooksDirError guard, not a substitute for it.

Run from skills/deliver/: python3 -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.install_hooks import MARKER, HookConflictError, SharedHooksDirError, hooks_dir, install, uninstall

_DELIVER_ROOT = Path(__file__).resolve().parent.parent
_FAKE_PYTHON = "/usr/bin/fake-python3"


class _Result:
    def __init__(self, stdout):
        self.stdout = stdout


def _fake_run(hooks_path: Path, common_dir_hooks_path: Path):
    """Answers `git rev-parse --git-path hooks` with `hooks_path` and
    `git rev-parse --git-common-dir` with `common_dir_hooks_path`'s
    parent -- i.e. the repo-local hooks dir install_hooks compares
    `hooks_path` against to decide whether it's shared."""
    def run(args, **kwargs):
        if args[:4] == ["git", "rev-parse", "--git-path", "hooks"]:
            return _Result(stdout=f"{hooks_path}\n")
        if args[:3] == ["git", "rev-parse", "--git-common-dir"]:
            return _Result(stdout=f"{common_dir_hooks_path.parent}\n")
        raise AssertionError(f"unexpected git call in a test that must never shell out for real: {args}")

    return run


def _fake_run_repo_local(target_dir: Path):
    """The ordinary, non-shared case: --git-path hooks and --git-common-dir
    agree that `target_dir` IS this repo's own local hooks dir."""
    return _fake_run(target_dir, target_dir)


def _run_isolated(args, cwd):
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env=env)


def _init_repo_isolated(root: Path) -> None:
    _run_isolated(["git", "init", "-q", "-b", "main"], root)
    _run_isolated(["git", "config", "user.email", "x@x.com"], root)
    _run_isolated(["git", "config", "user.name", "x"], root)


class InstallTests(unittest.TestCase):
    def test_writes_both_hooks_with_the_marker_and_a_runtime_repo_root_lookup(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"

            installed = install(repo, _DELIVER_ROOT, run=_fake_run_repo_local(target_dir), python_executable=_FAKE_PYTHON)

            self.assertEqual(set(installed), {"pre-commit", "pre-push"})
            for name in ("pre-commit", "pre-push"):
                content = (target_dir / name).read_text(encoding="utf-8")
                lines = content.splitlines()
                self.assertEqual(lines[1], MARKER)
                self.assertIn(str((_DELIVER_ROOT / "scripts" / "hook_runner.py").resolve()), content)
                self.assertIn(_FAKE_PYTHON, content)
                # The repo root is looked up at runtime (worktree-correct), never baked in.
                self.assertIn("git rev-parse --show-toplevel", content)
                self.assertNotIn(str(repo), content)
                if sys.platform != "win32":
                    self.assertTrue((target_dir / name).stat().st_mode & 0o100)

    def test_refuses_to_overwrite_an_unrelated_existing_hook(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"
            target_dir.mkdir()
            (target_dir / "pre-commit").write_text("#!/bin/sh\necho someone-elses-hook\n", encoding="utf-8")

            with self.assertRaises(HookConflictError):
                install(repo, _DELIVER_ROOT, run=_fake_run_repo_local(target_dir))

            # Nothing was written for the other hook either -- install is all-or-nothing.
            self.assertFalse((target_dir / "pre-push").exists())

    def test_treats_a_symlink_at_a_hook_name_as_not_ours_rather_than_crashing(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"
            target_dir.mkdir()
            elsewhere = Path(root) / "elsewhere.txt"
            elsewhere.write_text("not a hook\n", encoding="utf-8")
            (target_dir / "pre-commit").symlink_to(elsewhere)

            with self.assertRaises(HookConflictError):
                install(repo, _DELIVER_ROOT, run=_fake_run_repo_local(target_dir))

    def test_refuses_a_shared_hooks_directory_by_default(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            shared = Path(root) / "shared-global-hooks"
            local = Path(root) / "repo" / ".git" / "hooks"

            with self.assertRaises(SharedHooksDirError):
                install(repo, _DELIVER_ROOT, run=_fake_run(shared, local))

            self.assertFalse(shared.exists())

    def test_installs_into_a_shared_hooks_directory_when_explicitly_allowed(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            shared = Path(root) / "shared-global-hooks"
            local = Path(root) / "repo" / ".git" / "hooks"

            installed = install(repo, _DELIVER_ROOT, run=_fake_run(shared, local), allow_shared_hooks_dir=True)

            self.assertEqual(set(installed), {"pre-commit", "pre-push"})


class UninstallTests(unittest.TestCase):
    def test_removes_only_marker_carrying_hooks(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"
            fake_run = _fake_run_repo_local(target_dir)
            install(repo, _DELIVER_ROOT, run=fake_run)
            (target_dir / "pre-push").unlink()
            (target_dir / "pre-push").write_text("#!/bin/sh\necho someone-elses-hook\n", encoding="utf-8")

            removed = uninstall(repo, run=fake_run)

            self.assertEqual(removed, ["pre-commit"])
            self.assertFalse((target_dir / "pre-commit").exists())
            self.assertTrue((target_dir / "pre-push").exists())


class WorktreeAndIsolationTests(unittest.TestCase):
    def test_worktree_resolves_to_the_same_shared_hooks_directory_and_real_install_works_there(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "main"
            repo.mkdir()
            _init_repo_isolated(repo)
            (repo / "f.txt").write_text("x\n", encoding="utf-8")
            _run_isolated(["git", "add", "-A"], repo)
            _run_isolated(["git", "commit", "-q", "--no-verify", "-m", "init"], repo)
            worktree = Path(root) / "wt"
            _run_isolated(["git", "worktree", "add", str(worktree), "-b", "feature"], repo)

            self.assertEqual(hooks_dir(repo), hooks_dir(worktree))

            # A real install, from the worktree, isolated from this machine's
            # real global config by GIT_CONFIG_GLOBAL/NOSYSTEM above -- proves
            # install() actually works end-to-end from a worktree, not just
            # that path resolution agrees.
            def isolated_run(args, **kwargs):
                env = dict(os.environ)
                env["GIT_CONFIG_GLOBAL"] = os.devnull
                env["GIT_CONFIG_NOSYSTEM"] = "1"
                kwargs["env"] = env
                return subprocess.run(args, **kwargs)

            installed = install(worktree, _DELIVER_ROOT, run=isolated_run)
            self.assertEqual(set(installed), {"pre-commit", "pre-push"})
            self.assertTrue((hooks_dir(repo) / "pre-commit").exists())


if __name__ == "__main__":
    unittest.main()
