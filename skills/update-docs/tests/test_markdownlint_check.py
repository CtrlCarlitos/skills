"""Tests for the optional markdownlint-cli2 wrapper: installed binary
wins, npx is the fallback when only Node is present, no linter available
means the check is skipped (never a hard dependency or a hard failure),
and the call runs through the shell on Windows specifically -- confirmed
live in release-notes' own CI that npx/markdownlint-cli2 are .cmd shims
there and subprocess can't CreateProcess those directly otherwise.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.markdownlint_check import check_markdown, find_markdownlint


def _which_only(*names):
    allowed = set(names)
    return lambda name: f"/usr/bin/{name}" if name in allowed else None


class FindMarkdownlintTests(unittest.TestCase):
    def test_prefers_an_installed_binary(self):
        which = _which_only("markdownlint-cli2", "npx")

        self.assertEqual(find_markdownlint(which=which), ["markdownlint-cli2"])

    def test_falls_back_to_npx(self):
        which = _which_only("npx")

        self.assertEqual(find_markdownlint(which=which), ["npx", "--yes", "markdownlint-cli2"])

    def test_returns_none_when_neither_is_available(self):
        self.assertIsNone(find_markdownlint(which=_which_only()))


class CheckMarkdownTests(unittest.TestCase):
    def test_skips_without_failing_when_unavailable(self):
        result = check_markdown("doc.md", which=_which_only())

        self.assertFalse(result["ran"])
        self.assertTrue(result["passed"])

    def test_reports_success(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        result = check_markdown("doc.md", which=_which_only("markdownlint-cli2"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertTrue(result["passed"])

    def test_reports_failure_with_output(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 1
                stdout = "doc.md:3 MD013/line-length\n"
                stderr = ""

            return R()

        result = check_markdown("doc.md", which=_which_only("markdownlint-cli2"), run=fake_run)

        self.assertFalse(result["passed"])
        self.assertIn("MD013", result["output"])

    def test_runs_through_the_shell_on_windows(self):
        kwargs_seen = {}

        def fake_run(args, **kwargs):
            kwargs_seen.update(kwargs)

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        check_markdown("doc.md", which=_which_only("markdownlint-cli2"), run=fake_run, system=lambda: "Windows")

        self.assertTrue(kwargs_seen.get("shell"))

    def test_does_not_use_the_shell_on_non_windows(self):
        kwargs_seen = {}

        def fake_run(args, **kwargs):
            kwargs_seen.update(kwargs)

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        check_markdown("doc.md", which=_which_only("markdownlint-cli2"), run=fake_run, system=lambda: "Linux")

        self.assertFalse(kwargs_seen.get("shell"))

    def test_accepts_several_paths_in_one_invocation(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        check_markdown(["a.md", "b.md"], which=_which_only("markdownlint-cli2"), run=fake_run)

        self.assertEqual(calls, [["markdownlint-cli2", "a.md", "b.md"]])

    def test_passes_cwd_through_so_a_repos_own_config_auto_discovers(self):
        """With no explicit --config, markdownlint-cli2 auto-discovers a
        target repo's own config by walking up from its cwd -- so the
        repo being audited, not wherever this process happens to be
        running from, must be the subprocess's cwd."""
        kwargs_seen = {}

        def fake_run(args, **kwargs):
            kwargs_seen.update(kwargs)

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        check_markdown("doc.md", cwd="/some/repo", which=_which_only("markdownlint-cli2"), run=fake_run)

        self.assertEqual(kwargs_seen.get("cwd"), "/some/repo")


if __name__ == "__main__":
    unittest.main()
