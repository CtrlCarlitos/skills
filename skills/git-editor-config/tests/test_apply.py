"""Tests for apply.py. The exec-bit tests use a real local git repo built
in a tmp dir, not mocked subprocess output -- the whole point of this
module is that it only touches what it's told to, which is best proven
against real `git ls-files -s` / file-system state.

Run from skills/git-editor-config/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.apply import apply_exec_bit_fixes, apply_gitattributes_rules


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
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            readme_before = (repo / "README.md").read_bytes()

            apply_exec_bit_fixes(repo, [{"path": "run.sh", "drift": "missing"}])

            self.assertEqual((repo / "README.md").read_bytes(), readme_before)


if __name__ == "__main__":
    unittest.main()
