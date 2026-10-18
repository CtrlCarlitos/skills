"""Tests for doc-file discovery and the Rule 6 exclusions ("hands off
other records"): CHANGELOG.md (that's release-notes' territory) and
accepted ADRs are never surfaced as audit findings at all, not just
protected from editing.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.doc_files import discover_doc_files, is_doc_path, is_excluded_record


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


class IsExcludedRecordTests(unittest.TestCase):
    def test_changelog_md_is_excluded(self):
        self.assertTrue(is_excluded_record("CHANGELOG.md"))

    def test_a_nested_changelog_is_excluded(self):
        self.assertTrue(is_excluded_record("packages/core/CHANGELOG.md"))

    def test_an_adr_under_a_docs_adr_directory_is_excluded(self):
        self.assertTrue(is_excluded_record("docs/adr/0001-use-postgres.md"))

    def test_an_adr_under_a_decisions_directory_is_excluded(self):
        self.assertTrue(is_excluded_record("decisions/0002-pick-a-queue.md"))

    def test_an_ordinary_doc_is_not_excluded(self):
        self.assertFalse(is_excluded_record("docs/getting-started.md"))


class IsDocPathTests(unittest.TestCase):
    def test_a_markdown_file_is_a_doc(self):
        self.assertTrue(is_doc_path("docs/guide.md"))

    def test_a_readme_with_no_extension_is_a_doc(self):
        self.assertTrue(is_doc_path("README"))

    def test_an_rst_file_is_a_doc(self):
        self.assertTrue(is_doc_path("docs/index.rst"))

    def test_a_python_source_file_is_not_a_doc(self):
        self.assertFalse(is_doc_path("src/app.py"))

    def test_a_changelog_is_not_a_doc_for_this_skills_purposes(self):
        self.assertFalse(is_doc_path("CHANGELOG.md"))

    def test_an_adr_is_not_a_doc_for_this_skills_purposes(self):
        self.assertFalse(is_doc_path("docs/adr/0001-use-postgres.md"))


class DiscoverDocFilesTests(unittest.TestCase):
    def test_discovers_tracked_doc_files_and_excludes_changelog_and_adrs(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            (root / "README.md").write_text("# Project\n", encoding="utf-8")
            (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
            (root / "docs" / "adr").mkdir()
            (root / "docs" / "adr" / "0001-use-postgres.md").write_text("# ADR\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            _run(["git", "add", "-A"], root)
            _run(["git", "commit", "-q", "-m", "init"], root)

            found = discover_doc_files(root)

            self.assertEqual(set(found), {"README.md", "docs/guide.md"})

    def test_an_untracked_doc_file_is_not_discovered(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            (root / "README.md").write_text("# Project\n", encoding="utf-8")
            _run(["git", "add", "-A"], root)
            _run(["git", "commit", "-q", "-m", "init"], root)
            (root / "untracked.md").write_text("# Not tracked\n", encoding="utf-8")

            found = discover_doc_files(root)

            self.assertEqual(found, ["README.md"])


if __name__ == "__main__":
    unittest.main()
