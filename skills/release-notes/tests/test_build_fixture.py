"""Tests for the fixture-builder that turns an evals.json scenario's `ops`
list into a real git repo -- so evals/evals.json's fixtures are actually
executable against the real modules, not just descriptive text.

Run from skills/release-notes/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

import subprocess

from scripts.build_fixture import build_fixture
from scripts.commits import list_commits
from scripts.range import resolve_range


class BuildFixtureTests(unittest.TestCase):
    def test_commit_ops_write_files_and_commit_them_in_order(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            ops = [
                {"commit": "first", "files": {"a.txt": "1"}},
                {"commit": "second", "files": {"b.txt": "2"}},
            ]

            build_fixture(ops, root)

            first_sha = subprocess.run(
                ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=root, capture_output=True, text=True, check=True
            ).stdout.strip()
            commits = list_commits(root, base=first_sha, head="HEAD")
            self.assertEqual([c["subject"] for c in commits], ["second"])
            self.assertTrue((root / "a.txt").is_file())
            self.assertTrue((root / "b.txt").is_file())

    def test_tag_ops_create_a_real_tag(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            ops = [
                {"commit": "first", "files": {"a.txt": "1"}},
                {"tag": "v1.0.0"},
                {"commit": "second", "files": {"b.txt": "2"}},
            ]

            build_fixture(ops, root)

            result = resolve_range(root)
            self.assertEqual(result["base"], "v1.0.0")

    def test_revert_ops_create_a_real_revert_commit(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            ops = [
                {"commit": "base", "files": {"base.txt": "base"}},
                {"tag": "v1.0.0"},
                {"commit": "feat: add thing", "files": {"thing.txt": "x"}},
                {"revert": "HEAD"},
            ]

            build_fixture(ops, root)

            commits = list_commits(root, base="v1.0.0", head="HEAD")
            self.assertEqual([c["subject"] for c in commits], ["feat: add thing", 'Revert "feat: add thing"'])

    def test_files_can_be_nested_in_subdirectories(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            ops = [{"commit": "first", "files": {"migrations/0001_init.py": "pass\n"}}]

            build_fixture(ops, root)

            self.assertEqual((root / "migrations" / "0001_init.py").read_text(encoding="utf-8"), "pass\n")

    def test_raises_a_clear_error_on_an_unknown_op(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)

            with self.assertRaises(ValueError) as ctx:
                build_fixture([{"mystery": "???"}], root)

            self.assertIn("mystery", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
