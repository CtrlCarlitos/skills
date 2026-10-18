"""Tests for gitignore_audit. The unignored-file checks use a real local
git repo built in a tmp dir, not mocked subprocess output -- this is about
correctly parsing `git status --porcelain --ignored=no`'s own output.

Run from skills/git-editor-config/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.gitignore_audit import find_tracked_generated_files, find_unignored_generated_files


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


class FindTrackedGeneratedFilesTests(unittest.TestCase):
    def test_flags_binary_signal(self):
        files = [
            {"path": "build/out.bin", "mode": "100644", "has_shebang": False, "is_binary": True},
            {"path": "src/main.py", "mode": "100644", "has_shebang": False, "is_binary": False},
        ]

        gaps = find_tracked_generated_files(files)

        self.assertEqual([g["path"] for g in gaps], ["build/out.bin"])


class FindUnignoredGeneratedFilesTests(unittest.TestCase):
    def test_reports_untracked_binary_file(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            _run(["git", "add", "README.md"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            (repo / "cache.bin").write_bytes(b"\x00\x01binary")

            gaps = find_unignored_generated_files(repo)

            self.assertEqual([g["path"] for g in gaps], ["cache.bin"])

    def test_skips_already_ignored_file(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / ".gitignore").write_text("*.bin\n", encoding="utf-8")
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            _run(["git", "add", "README.md", ".gitignore"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            (repo / "cache.bin").write_bytes(b"\x00\x01binary")

            self.assertEqual(find_unignored_generated_files(repo), [])


if __name__ == "__main__":
    unittest.main()
