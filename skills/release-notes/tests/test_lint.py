"""Tests for the optional markdownlint-cli2 wrapper: installed binary wins,
npx is the fallback when only Node is present, and no linter available
means the lint step is skipped -- never a hard failure or a hard
dependency. Uses injected fakes for `which`/`run`, not a real subprocess,
since this is about selection logic, not markdownlint-cli2's own behavior.

Run from skills/release-notes/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.lint import find_linter, lint_file


def _which_only(*names):
    allowed = set(names)
    return lambda name: f"/usr/bin/{name}" if name in allowed else None


class FindLinterTests(unittest.TestCase):
    def test_prefers_an_installed_markdownlint_cli2_binary(self):
        which = _which_only("markdownlint-cli2", "npx")

        self.assertEqual(find_linter(which=which), ["markdownlint-cli2"])

    def test_falls_back_to_npx_when_only_node_tooling_is_present(self):
        which = _which_only("npx")

        self.assertEqual(find_linter(which=which), ["npx", "--yes", "markdownlint-cli2"])

    def test_returns_none_when_neither_is_available(self):
        which = _which_only()

        self.assertIsNone(find_linter(which=which))


class LintFileTests(unittest.TestCase):
    def test_skips_without_failing_when_no_linter_is_available(self):
        result = lint_file("CHANGELOG.md", which=_which_only())

        self.assertFalse(result["ran"])
        self.assertTrue(result["passed"])

    def test_runs_the_found_linter_and_reports_success(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class FakeResult:
                returncode = 0
                stdout = ""
                stderr = ""

            return FakeResult()

        result = lint_file("CHANGELOG.md", which=_which_only("markdownlint-cli2"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertTrue(result["passed"])
        self.assertEqual(calls, [["markdownlint-cli2", "CHANGELOG.md"]])

    def test_runs_the_found_linter_and_reports_failure_with_its_output(self):
        def fake_run(args, **kwargs):
            class FakeResult:
                returncode = 1
                stdout = "CHANGELOG.md:3 MD013/line-length\n"
                stderr = ""

            return FakeResult()

        result = lint_file("CHANGELOG.md", which=_which_only("markdownlint-cli2"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertFalse(result["passed"])
        self.assertIn("MD013", result["output"])

    def test_passes_a_config_path_through_when_given(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class FakeResult:
                returncode = 0
                stdout = ""
                stderr = ""

            return FakeResult()

        lint_file(
            "CHANGELOG.md",
            config_path=".markdownlint-cli2.jsonc",
            which=_which_only("markdownlint-cli2"),
            run=fake_run,
        )

        self.assertEqual(calls, [["markdownlint-cli2", "--config", ".markdownlint-cli2.jsonc", "CHANGELOG.md"]])


if __name__ == "__main__":
    unittest.main()
