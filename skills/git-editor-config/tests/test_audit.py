"""Tests for the scripts.audit CLI entry point.

Run from skills/git-editor-config/: python3 -m unittest discover -s tests
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


class AuditCliTests(unittest.TestCase):
    def test_reports_a_real_gap_on_a_fresh_repo(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "deploy.patch").write_text("--- a\n+++ b\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit", str(repo)],
                cwd=_SKILL_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("deploy.patch", result.stdout)
            self.assertIn("eol=lf", result.stdout)

    def test_does_not_crash_with_an_untracked_binary_file_present(self):
        # Regression: the .gitignore check used to omit "reason" from its
        # row, which crashed report.py's rendering the moment this exact
        # scenario -- the one the check exists to find -- actually occurred.
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            (repo / "cache.bin").write_bytes(b"\x00\x01binary")

            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit", str(repo)],
                cwd=_SKILL_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("cache.bin", result.stdout)


if __name__ == "__main__":
    unittest.main()
