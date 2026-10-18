"""Tests for the optional lychee link-checker wrapper: installed binary
used if present, otherwise the check is skipped (never a hard
dependency). Unlike markdownlint-cli2, lychee has no npx-style fallback
-- it's a native binary with no universal package-manager shim, so
"not installed" just means "skipped".

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.linkcheck import check_links, find_linkchecker


def _which_only(*names):
    allowed = set(names)
    return lambda name: f"/usr/bin/{name}" if name in allowed else None


class FindLinkcheckerTests(unittest.TestCase):
    def test_uses_an_installed_lychee(self):
        self.assertEqual(find_linkchecker(which=_which_only("lychee")), ["lychee"])

    def test_returns_none_when_not_installed(self):
        self.assertIsNone(find_linkchecker(which=_which_only()))


class CheckLinksTests(unittest.TestCase):
    def test_skips_without_failing_when_unavailable(self):
        result = check_links("doc.md", which=_which_only())

        self.assertFalse(result["ran"])
        self.assertTrue(result["passed"])
        self.assertEqual(result["broken"], [])

    def test_reports_success_when_lychees_json_shows_no_errors(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 0
                stdout = json.dumps({"errors": 0, "error_map": {}})
                stderr = ""

            return R()

        result = check_links("doc.md", which=_which_only("lychee"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertTrue(result["passed"])
        self.assertEqual(result["broken"], [])

    def test_reports_the_broken_links_from_lychees_json(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 2
                stdout = json.dumps({
                    "errors": 1,
                    "error_map": {
                        "doc.md": [
                            {
                                "url": "https://example.com/dead",
                                "status": {"text": "Rejected status code: 404 Not Found", "code": 404},
                                "span": {"line": 3, "column": 5},
                            }
                        ]
                    },
                })
                stderr = ""

            return R()

        result = check_links("doc.md", which=_which_only("lychee"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["broken"]), 1)
        self.assertEqual(result["broken"][0]["url"], "https://example.com/dead")
        self.assertEqual(result["broken"][0]["line"], 3)

    def test_passes_a_config_path_through_when_given(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class R:
                returncode = 0
                stdout = json.dumps({"errors": 0, "error_map": {}})
                stderr = ""

            return R()

        check_links("doc.md", config_path="lychee.toml", which=_which_only("lychee"), run=fake_run)

        self.assertEqual(calls, [["lychee", "--format", "json", "--config", "lychee.toml", "doc.md"]])

    def test_accepts_several_paths_in_one_invocation(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class R:
                returncode = 0
                stdout = json.dumps({"errors": 0, "error_map": {}})
                stderr = ""

            return R()

        check_links(["a.md", "b.md"], which=_which_only("lychee"), run=fake_run)

        self.assertEqual(calls, [["lychee", "--format", "json", "a.md", "b.md"]])

    def test_passes_cwd_through_so_a_repos_own_config_auto_discovers(self):
        kwargs_seen = {}

        def fake_run(args, **kwargs):
            kwargs_seen.update(kwargs)

            class R:
                returncode = 0
                stdout = json.dumps({"errors": 0, "error_map": {}})
                stderr = ""

            return R()

        check_links("doc.md", cwd="/some/repo", which=_which_only("lychee"), run=fake_run)

        self.assertEqual(kwargs_seen.get("cwd"), "/some/repo")


@unittest.skipUnless(shutil.which("lychee"), "lychee is not installed in this environment")
class RealLycheeTests(unittest.TestCase):
    def test_a_real_broken_link_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "doc.md"
            path.write_text(
                "# Doc\n\nSee [this](https://github.com/CtrlCarlitos/this-repo-does-not-exist-404).\n",
                encoding="utf-8",
            )

            result = check_links(str(path))

            self.assertTrue(result["ran"])
            self.assertFalse(result["passed"])
            self.assertEqual(len(result["broken"]), 1)
            self.assertIn("this-repo-does-not-exist-404", result["broken"][0]["url"])

    def test_a_real_working_link_passes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "doc.md"
            path.write_text("# Doc\n\nSee [GitHub](https://github.com).\n", encoding="utf-8")

            result = check_links(str(path))

            self.assertTrue(result["ran"])
            self.assertTrue(result["passed"])
            self.assertEqual(result["broken"], [])


if __name__ == "__main__":
    unittest.main()
