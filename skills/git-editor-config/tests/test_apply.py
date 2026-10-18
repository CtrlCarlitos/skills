"""Tests for apply.py. The exec-bit tests use a real local git repo built
in a tmp dir, not mocked subprocess output -- the whole point of this
module is that it only touches what it's told to, which is best proven
against real `git ls-files -s` / file-system state.

Run from skills/git-editor-config/: python3 -m unittest discover -s tests
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.apply import (
    apply_editorconfig_sections,
    apply_exec_bit_fixes,
    apply_gitattributes_rules,
    apply_gitignore_patterns,
)


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


class ApplyGitattributesRulesTests(unittest.TestCase):
    def test_appends_only_approved_rows(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            (repo / ".gitattributes").write_text("*.sh text eol=lf\n", encoding="utf-8")

            apply_gitattributes_rules(repo, [{"path": "deploy.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "x"}])

            content = (repo / ".gitattributes").read_text(encoding="utf-8")
            self.assertEqual(content, "*.sh text eol=lf\ndeploy.patch text eol=lf -diff\n")

    def test_adds_a_missing_trailing_newline_before_appending_rather_than_joining_lines(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            (repo / ".gitattributes").write_bytes(b"*.sh text eol=lf")  # no trailing newline

            apply_gitattributes_rules(repo, [{"path": "deploy.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "x"}])

            content = (repo / ".gitattributes").read_bytes()
            self.assertEqual(content, b"*.sh text eol=lf\ndeploy.patch text eol=lf -diff\n")

    def test_preserves_existing_crlf_bytes_exactly(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            (repo / ".gitattributes").write_bytes(b"*.sh text eol=lf\r\n")

            apply_gitattributes_rules(repo, [{"path": "deploy.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "x"}])

            content = (repo / ".gitattributes").read_bytes()
            self.assertEqual(content, b"*.sh text eol=lf\r\ndeploy.patch text eol=lf -diff\n")

    def test_empty_approval_does_not_create_a_file(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)

            apply_gitattributes_rules(repo, [])

            self.assertFalse((repo / ".gitattributes").exists())

    def test_quotes_a_path_containing_whitespace(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)

            apply_gitattributes_rules(repo, [{"path": "my fix.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "x"}])

            content = (repo / ".gitattributes").read_text(encoding="utf-8")
            self.assertEqual(content, '"my fix.patch" text eol=lf -diff\n')


class ApplyGitignorePatternsTests(unittest.TestCase):
    def test_appends_only_approved_rows(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            (repo / ".gitignore").write_bytes(b"node_modules")  # no trailing newline

            apply_gitignore_patterns(repo, [{"path": "cache.bin", "reason": "x"}])

            content = (repo / ".gitignore").read_bytes()
            self.assertEqual(content, b"node_modules\ncache.bin\n")

    def test_empty_approval_does_not_create_a_file(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)

            apply_gitignore_patterns(repo, [])

            self.assertFalse((repo / ".gitignore").exists())


class ApplyEditorconfigSectionsTests(unittest.TestCase):
    def test_appends_a_section_for_each_approved_extension(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            (repo / ".editorconfig").write_bytes(b"root = true")  # no trailing newline

            apply_editorconfig_sections(repo, [{"extension": ".py", "example_path": "a.py"}], {"indent_style": "space"})

            content = (repo / ".editorconfig").read_bytes()
            self.assertEqual(content, b"root = true\n\n[*.py]\nindent_style = space\n")

    def test_empty_approval_does_not_create_a_file(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)

            apply_editorconfig_sections(repo, [], {"indent_style": "space"})

            self.assertFalse((repo / ".editorconfig").exists())


class ApplyExecBitFixesTests(unittest.TestCase):
    def test_only_changes_named_files(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "run.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            (repo / "other.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            apply_exec_bit_fixes(repo, [{"path": "run.sh", "drift": "missing"}])

            modes = subprocess.run(["git", "ls-files", "-s"], cwd=repo, capture_output=True, text=True, check=True).stdout
            by_path = {line.split("\t", 1)[1]: line.split()[0] for line in modes.splitlines()}
            self.assertEqual(by_path["run.sh"], "100755")
            self.assertEqual(by_path["other.sh"], "100644")

    def test_only_touches_named_files_rest_of_tree_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            (repo / "run.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            (repo / "other.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            readme_before = (repo / "README.md").read_bytes()
            other_mode_before = (repo / "other.sh").stat().st_mode

            apply_exec_bit_fixes(repo, [{"path": "run.sh", "drift": "missing"}])

            self.assertEqual((repo / "README.md").read_bytes(), readme_before)
            self.assertEqual((repo / "other.sh").stat().st_mode, other_mode_before)

    @unittest.skipIf(sys.platform == "win32", "NTFS has no POSIX executable bit to sync")
    def test_also_updates_the_working_tree_file_mode_not_just_the_index(self):
        # A fix that only touches the git index is invisible to `ls -l` and
        # gets silently reverted by the next `git add -A`/`commit -a` on a
        # filemode=true checkout -- the index and working tree must agree.
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "run.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            apply_exec_bit_fixes(repo, [{"path": "run.sh", "drift": "missing"}])

            real_mode = (repo / "run.sh").stat().st_mode
            self.assertTrue(real_mode & 0o100, "working-tree file should now be executable")

    def test_handles_a_path_starting_with_a_dash(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "-run.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            apply_exec_bit_fixes(repo, [{"path": "-run.sh", "drift": "missing"}])

            modes = subprocess.run(["git", "ls-files", "-s"], cwd=repo, capture_output=True, text=True, check=True).stdout
            self.assertIn("100755", modes)


if __name__ == "__main__":
    unittest.main()
