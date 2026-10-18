"""Tests for install_hooks: install/uninstall a tiny pre-commit/pre-push
hook pair, worktree-safe, never touching a hook this tool didn't write.

All install/uninstall tests inject a fake `run` that resolves
`git rev-parse --git-path hooks` to a path under the fixture's own tmp
directory -- never the real `git rev-parse` call. This isn't a shortcut:
a machine can have `core.hooksPath` configured globally (this one does),
which makes the real call resolve to the SAME shared directory for every
repo on the machine, including a disposable tmp fixture. A test that
exercised the real resolution during a file-WRITE discovered this the
hard way, writing fixture content into a real, pre-existing file outside
any test's control. Only `WorktreeResolutionTests` below calls the real
`git rev-parse` (read-only, never a write), to prove the one property
that genuinely needs live git: a worktree and its main checkout resolve
to the identical hooks directory.

Run from skills/deliver/: python3 -m unittest discover -s tests
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.install_hooks import MARKER, HookConflictError, hooks_dir, install, uninstall


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


def _fake_run_resolving_to(hooks_path: Path):
    """A stand-in for subprocess.run that answers `git rev-parse --git-path
    hooks` with a fixed, test-owned path -- used by every test below that
    writes files, so none of them can ever touch this machine's real,
    possibly-global hooks directory."""
    class _Result:
        def __init__(self, stdout):
            self.stdout = stdout

    def run(args, **kwargs):
        assert args[:4] == ["git", "rev-parse", "--git-path", "hooks"]
        return _Result(stdout=f"{hooks_path}\n")

    return run


_DELIVER_ROOT = Path(__file__).resolve().parent.parent


class InstallTests(unittest.TestCase):
    def test_writes_both_hooks_with_the_marker_and_an_absolute_runner_path(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"
            fake_run = _fake_run_resolving_to(target_dir)

            installed = install(repo, _DELIVER_ROOT, run=fake_run)

            self.assertEqual(set(installed), {"pre-commit", "pre-push"})
            for name in ("pre-commit", "pre-push"):
                content = (target_dir / name).read_text(encoding="utf-8")
                self.assertIn(MARKER, content)
                self.assertIn(str(_DELIVER_ROOT / "scripts" / "hook_runner.py"), content)
                self.assertIn(str(repo), content)
                if sys.platform != "win32":
                    self.assertTrue((target_dir / name).stat().st_mode & 0o100)

    def test_refuses_to_overwrite_an_unrelated_existing_hook(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"
            target_dir.mkdir()
            (target_dir / "pre-commit").write_text("#!/bin/sh\necho someone-elses-hook\n", encoding="utf-8")
            fake_run = _fake_run_resolving_to(target_dir)

            with self.assertRaises(HookConflictError):
                install(repo, _DELIVER_ROOT, run=fake_run)

            # Nothing was written for the other hook either -- install is all-or-nothing.
            self.assertFalse((target_dir / "pre-push").exists())


class UninstallTests(unittest.TestCase):
    def test_removes_only_marker_carrying_hooks(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            target_dir = Path(root) / "hooks"
            fake_run = _fake_run_resolving_to(target_dir)
            install(repo, _DELIVER_ROOT, run=fake_run)
            (target_dir / "pre-push").unlink()
            (target_dir / "pre-push").write_text("#!/bin/sh\necho someone-elses-hook\n", encoding="utf-8")

            removed = uninstall(repo, run=fake_run)

            self.assertEqual(removed, ["pre-commit"])
            self.assertFalse((target_dir / "pre-commit").exists())
            self.assertTrue((target_dir / "pre-push").exists())


class WorktreeResolutionTests(unittest.TestCase):
    def test_worktree_resolves_to_the_same_shared_hooks_directory(self):
        # Read-only: only `git rev-parse --git-path hooks` is called for
        # real here, on both the main checkout and its worktree -- nothing
        # in this test writes a hook file, so it can't collide with
        # whatever this machine's hooks path actually resolves to.
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "main"
            repo.mkdir()
            _init_repo(repo)
            (repo / "f.txt").write_text("x\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            worktree = Path(root) / "wt"
            _run(["git", "worktree", "add", str(worktree), "-b", "feature"], repo)

            self.assertEqual(hooks_dir(repo), hooks_dir(worktree))


if __name__ == "__main__":
    unittest.main()
