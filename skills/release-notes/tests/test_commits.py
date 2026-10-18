"""Tests for commit gathering, revert-pair collapsing, and squash-merge
PR-reference extraction. Uses real git repos and a real `git revert` --
confirmed live first that git's revert trailer is "This reverts commit
<full 40-char SHA>." in the commit BODY (not subject, not abbreviated).

Run from skills/release-notes/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.commits import collapse_reverted_pairs, extract_pr_reference, list_commits


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


def _commit(root: Path, message: str, filename: str = "file.txt", content: str | None = None) -> str:
    (root / filename).write_text(content if content is not None else message, encoding="utf-8")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)
    return _run(["git", "rev-parse", "HEAD"], root).stdout.strip()


class ListCommitsTests(unittest.TestCase):
    def test_lists_commits_in_the_range_oldest_first(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "first")
            _run(["git", "tag", "v1.0.0"], root)
            _commit(root, "second")
            _commit(root, "third")

            commits = list_commits(root, base="v1.0.0", head="HEAD")

            self.assertEqual([c["subject"] for c in commits], ["second", "third"])

    def test_each_commit_has_its_real_sha_and_parents(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            first_sha = _commit(root, "first")
            _run(["git", "tag", "v1.0.0"], root)
            second_sha = _commit(root, "second")

            commits = list_commits(root, base="v1.0.0", head="HEAD")

            self.assertEqual(commits[0]["sha"], second_sha)
            self.assertEqual(commits[0]["parents"], [first_sha])
            self.assertFalse(commits[0]["is_merge"])


class CollapseRevertedPairsTests(unittest.TestCase):
    def test_a_commit_reverted_within_the_same_range_is_excluded_along_with_its_revert(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "base")
            _run(["git", "tag", "v1.0.0"], root)
            _commit(root, "feat: add thing")
            _run(["git", "revert", "--no-edit", "HEAD"], root)

            commits = list_commits(root, base="v1.0.0", head="HEAD")
            kept, not_included = collapse_reverted_pairs(commits)

            self.assertEqual(kept, [])
            self.assertEqual({c["subject"] for c in not_included}, {"feat: add thing", 'Revert "feat: add thing"'})

    def test_a_commit_not_reverted_is_kept(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "base")
            _run(["git", "tag", "v1.0.0"], root)
            _commit(root, "feat: add thing")

            commits = list_commits(root, base="v1.0.0", head="HEAD")
            kept, not_included = collapse_reverted_pairs(commits)

            self.assertEqual([c["subject"] for c in kept], ["feat: add thing"])
            self.assertEqual(not_included, [])

    def test_a_commit_reverted_in_a_prior_release_outside_this_range_is_kept(self):
        """The original ships in range 1; the revert happens in range 2.
        Auditing range 2 alone must not retroactively un-ship range 1's
        commit -- it was genuinely released, then reverted later."""
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "base", filename="base.txt")
            _run(["git", "tag", "v1.0.0"], root)
            _commit(root, "feat: add thing", filename="thing.txt")
            _run(["git", "tag", "v1.1.0"], root)
            _commit(root, "feat: unrelated", filename="unrelated.txt")
            _run(["git", "revert", "--no-edit", "HEAD~1"], root)

            commits = list_commits(root, base="v1.1.0", head="HEAD")
            kept, not_included = collapse_reverted_pairs(commits)

            kept_subjects = {c["subject"] for c in kept}
            self.assertIn("feat: unrelated", kept_subjects)
            self.assertIn('Revert "feat: add thing"', kept_subjects)


class ExtractPrReferenceTests(unittest.TestCase):
    def test_extracts_the_pr_number_from_a_github_squash_merge_subject(self):
        commit = {"subject": "feat: add retry logic (#123)", "body": ""}

        self.assertEqual(extract_pr_reference(commit), 123)

    def test_returns_none_when_the_subject_has_no_pr_reference(self):
        commit = {"subject": "feat: add retry logic", "body": ""}

        self.assertIsNone(extract_pr_reference(commit))


if __name__ == "__main__":
    unittest.main()
