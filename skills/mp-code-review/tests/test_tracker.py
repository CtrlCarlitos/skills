"""Tests for the self-sufficient issue/MR reference detection and fetch
mechanism that replaces upstream's dependency on Matt Pocock's
`setup-matt-pocock-skills` tracker doc (which dotfiles never installs --
see vendor/mp-code-review/DISPOSITION.md for the full rationale).

Uses real git repos for remote-detection (not mocked subprocess output,
since this is about parsing `git remote`'s actual output shape), and
plain unit tests for the regex/command-construction logic.

Run from skills/mp-code-review/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tracker import detect_remote_host, extract_issue_refs, fetch_commands_for


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo_with_remote(root: Path, url: str) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "remote", "add", "origin", url], root)


class DetectRemoteHostTests(unittest.TestCase):
    def test_detects_github_from_an_https_remote(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo_with_remote(root, "https://github.com/CtrlCarlitos/skills.git")

            self.assertEqual(detect_remote_host(root), "github")

    def test_detects_github_from_an_ssh_remote(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo_with_remote(root, "git@github.com:CtrlCarlitos/skills.git")

            self.assertEqual(detect_remote_host(root), "github")

    def test_detects_gitlab_from_an_https_remote(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo_with_remote(root, "https://gitlab.com/some-group/some-project.git")

            self.assertEqual(detect_remote_host(root), "gitlab")

    def test_returns_none_for_an_unrecognized_remote(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo_with_remote(root, "https://bitbucket.org/some-team/some-repo.git")

            self.assertIsNone(detect_remote_host(root))

    def test_detects_github_even_when_a_gitconfig_insteadof_rule_rewrites_the_url(self):
        """Confirmed live in this very environment: a global
        url.<base>.insteadOf rule rewrites https://github.com/X/ to a
        git@github-X: SSH alias. `git remote get-url` returns the
        rewritten form (no "github.com" left in it); `git config --get`
        returns the raw stored URL, which this must use instead."""
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo_with_remote(root, "https://github.com/CtrlCarlitos/skills.git")
            # Simulate an insteadOf rewrite active for this one clone, same
            # shape as the real multi-account alias confirmed above.
            _run(["git", "config", "url.git@github-alias:.insteadOf", "https://github.com/"], root)
            rewritten = _run(["git", "remote", "get-url", "origin"], root).stdout.strip()
            self.assertNotIn("github.com", rewritten)  # sanity: the rewrite is actually in effect

            self.assertEqual(detect_remote_host(root), "github")

    def test_returns_none_when_there_is_no_remote_at_all(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _run(["git", "init", "-q", "-b", "main"], root)

            self.assertIsNone(detect_remote_host(root))


class ExtractIssueRefsTests(unittest.TestCase):
    def test_extracts_a_plain_hash_reference(self):
        refs = extract_issue_refs(["fix(login): handle expired tokens (#123)"])

        self.assertEqual(refs, [{"kind": "issue", "number": 123}])

    def test_extracts_a_closes_keyword_reference(self):
        refs = extract_issue_refs(["feat: add retry logic\n\nCloses #45"])

        self.assertEqual(refs, [{"kind": "issue", "number": 45}])

    def test_extracts_a_gitlab_merge_request_reference(self):
        refs = extract_issue_refs(["fix: typo in README (!67)"])

        self.assertEqual(refs, [{"kind": "merge_request", "number": 67}])

    def test_extracts_multiple_distinct_references_across_several_messages(self):
        refs = extract_issue_refs(["fix: a (#1)", "feat: b\n\nCloses #2", "chore: c (!3)"])

        self.assertEqual(
            refs,
            [
                {"kind": "issue", "number": 1},
                {"kind": "issue", "number": 2},
                {"kind": "merge_request", "number": 3},
            ],
        )

    def test_deduplicates_the_same_reference_seen_more_than_once(self):
        refs = extract_issue_refs(["fix: a (#1)", "fix: a, again (#1)"])

        self.assertEqual(refs, [{"kind": "issue", "number": 1}])

    def test_returns_an_empty_list_when_nothing_matches(self):
        refs = extract_issue_refs(["chore: bump dependency versions"])

        self.assertEqual(refs, [])


class FetchCommandsForTests(unittest.TestCase):
    def test_github_issue_ref_tries_issue_then_pr(self):
        commands = fetch_commands_for("github", {"kind": "issue", "number": 123})

        self.assertEqual(commands, [["gh", "issue", "view", "123"], ["gh", "pr", "view", "123"]])

    def test_gitlab_issue_ref_uses_glab_issue(self):
        commands = fetch_commands_for("gitlab", {"kind": "issue", "number": 45})

        self.assertEqual(commands, [["glab", "issue", "view", "45"]])

    def test_gitlab_merge_request_ref_uses_glab_mr(self):
        commands = fetch_commands_for("gitlab", {"kind": "merge_request", "number": 67})

        self.assertEqual(commands, [["glab", "mr", "view", "67"]])

    def test_an_unrecognized_host_yields_no_commands(self):
        commands = fetch_commands_for(None, {"kind": "issue", "number": 1})

        self.assertEqual(commands, [])

    def test_a_merge_request_ref_on_github_yields_no_commands(self):
        """GitHub has no distinct "merge request" numbering -- a !N ref
        found in a GitHub repo's commit history isn't a GitHub convention
        and shouldn't be guessed at."""
        commands = fetch_commands_for("github", {"kind": "merge_request", "number": 67})

        self.assertEqual(commands, [])


if __name__ == "__main__":
    unittest.main()
