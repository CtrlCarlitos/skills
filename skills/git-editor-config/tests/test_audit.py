"""Tests for the scripts.audit CLI entry point.

Run from skills/git-editor-config/: python3 -m unittest discover -s tests
"""
import subprocess
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
                ["python3", "-m", "scripts.audit", str(repo)],
                cwd=_SKILL_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("deploy.patch", result.stdout)
            self.assertIn("eol=lf", result.stdout)


if __name__ == "__main__":
    unittest.main()
