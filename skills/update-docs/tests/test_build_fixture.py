"""Tests for the fixture-builder that turns an evals.json scenario's `ops`
list into a real git repo -- so evals/evals.json's fixtures are actually
executable against the real modules, not just descriptive text. Same
design as release-notes/scripts/build_fixture.py (reimplemented here
since each skill is self-contained, no cross-skill imports).

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from scripts.build_fixture import build_fixture


class BuildFixtureTests(unittest.TestCase):
    def test_commit_ops_write_files_and_commit_them(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            ops = [
                {"commit": "first", "files": {"a.txt": "1"}},
                {"commit": "second", "files": {"b.txt": "2"}},
            ]

            build_fixture(ops, root)

            self.assertTrue((root / "a.txt").is_file())
            self.assertTrue((root / "b.txt").is_file())

    def test_files_can_be_nested_in_subdirectories(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            ops = [{"commit": "first", "files": {"docs/guide.md": "# Guide\n"}}]

            build_fixture(ops, root)

            self.assertEqual((root / "docs" / "guide.md").read_text(encoding="utf-8"), "# Guide\n")

    def test_raises_a_clear_error_on_an_unknown_op(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)

            with self.assertRaises(ValueError) as ctx:
                build_fixture([{"mystery": "???"}], root)

            self.assertIn("mystery", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
