"""Tests for resolving which files a diff/range touches, so the default
audit mode scopes to the change (Rule 2) instead of walking the whole
repo. Uses real git repos, not mocked subprocess output.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.diff_scope import DiffScopeError, changed_files


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


def _commit(root: Path, files: dict, message: str) -> None:
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


class ChangedFilesTests(unittest.TestCase):
    def test_lists_files_changed_between_an_explicit_range(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, {"README.md": "v1", "src/app.py": "v1"}, "first")
            _run(["git", "tag", "v1.0.0"], root)
            _commit(root, {"src/app.py": "v2"}, "second")

            found = changed_files(root, base="v1.0.0", head="HEAD")

            self.assertEqual(found, ["src/app.py"])

    def test_lists_uncommitted_changes_against_head_when_no_base_is_given(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, {"README.md": "v1", "src/app.py": "v1"}, "first")
            (root / "src" / "app.py").write_text("v2 (uncommitted)", encoding="utf-8")

            found = changed_files(root)

            self.assertEqual(found, ["src/app.py"])

    def test_raises_when_the_directory_is_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)

            with self.assertRaises(DiffScopeError) as ctx:
                changed_files(root)
            self.assertIn("not a git repository", str(ctx.exception).lower())

    def test_raises_when_the_base_does_not_resolve(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, {"README.md": "v1"}, "first")

            with self.assertRaises(DiffScopeError) as ctx:
                changed_files(root, base="does-not-exist")
            self.assertIn("does-not-exist", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
