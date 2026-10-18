"""Tests for the optional vale prose-style wrapper. vale, unlike
markdownlint-cli2/lychee, needs an actual config to do anything -- with
none, it errors ("no config file found") rather than silently passing.
Per the issue: use the repo's own .vale.ini if it has one, otherwise this
skill's built-in config, which declares the Google developer
documentation style package and syncs it with `vale sync` on first use.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.prose_check import (
    check_prose,
    ensure_builtin_styles_synced,
    ensure_builtin_vale_config,
    find_vale,
    resolve_vale_config,
)


def _which_only(*names):
    allowed = set(names)
    return lambda name: f"/usr/bin/{name}" if name in allowed else None


class FindValeTests(unittest.TestCase):
    def test_uses_an_installed_vale(self):
        self.assertEqual(find_vale(which=_which_only("vale")), ["vale"])

    def test_returns_none_when_not_installed(self):
        self.assertIsNone(find_vale(which=_which_only()))


class ResolveValeConfigTests(unittest.TestCase):
    def test_a_repos_own_vale_ini_wins(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as builtin:
            root, builtin = Path(root), Path(builtin)
            (root / ".vale.ini").write_text("StylesPath = styles\n", encoding="utf-8")
            builtin_ini = builtin / ".vale.ini"
            builtin_ini.write_text("StylesPath = styles\nPackages = Google\n", encoding="utf-8")

            self.assertEqual(resolve_vale_config(root, builtin_ini), root / ".vale.ini")

    def test_falls_back_to_the_builtin_config_when_the_repo_has_none(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as builtin:
            root, builtin = Path(root), Path(builtin)
            builtin_ini = builtin / ".vale.ini"
            builtin_ini.write_text("StylesPath = styles\nPackages = Google\n", encoding="utf-8")

            self.assertEqual(resolve_vale_config(root, builtin_ini), builtin_ini)


class EnsureBuiltinValeConfigTests(unittest.TestCase):
    def test_copies_the_template_into_the_cache_dir_and_syncs_styles(self):
        with tempfile.TemporaryDirectory() as template_dir, tempfile.TemporaryDirectory() as cache_root:
            template_ini = Path(template_dir) / ".vale.ini"
            template_ini.write_text("StylesPath = styles\nPackages = Google\n", encoding="utf-8")
            cache_dir = Path(cache_root) / "vale-styles"
            # Simulate a successful sync by pre-creating what `vale sync` would produce.
            def fake_run(args, **kwargs):
                (cache_dir / "styles" / "Google").mkdir(parents=True, exist_ok=True)
                (cache_dir / "styles" / "Google" / "placeholder.yml").write_text("x", encoding="utf-8")

                class R:
                    returncode = 0

                return R()

            result = ensure_builtin_vale_config(cache_dir, template_ini, run=fake_run)

            self.assertEqual(result, cache_dir / ".vale.ini")
            self.assertEqual((cache_dir / ".vale.ini").read_text(encoding="utf-8"), template_ini.read_text(encoding="utf-8"))

    def test_returns_none_when_syncing_fails(self):
        with tempfile.TemporaryDirectory() as template_dir, tempfile.TemporaryDirectory() as cache_root:
            template_ini = Path(template_dir) / ".vale.ini"
            template_ini.write_text("StylesPath = styles\nPackages = Google\n", encoding="utf-8")
            cache_dir = Path(cache_root) / "vale-styles"

            def fake_run(args, **kwargs):
                class R:
                    returncode = 1

                return R()

            result = ensure_builtin_vale_config(cache_dir, template_ini, run=fake_run)

            self.assertIsNone(result)

    def test_does_not_resync_when_the_cache_already_has_styles(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class R:
                returncode = 0

            return R()

        with tempfile.TemporaryDirectory() as template_dir, tempfile.TemporaryDirectory() as cache_root:
            template_ini = Path(template_dir) / ".vale.ini"
            template_ini.write_text("StylesPath = styles\nPackages = Google\n", encoding="utf-8")
            cache_dir = Path(cache_root) / "vale-styles"
            (cache_dir / "styles" / "Google").mkdir(parents=True)
            (cache_dir / "styles" / "Google" / "placeholder.yml").write_text("x", encoding="utf-8")
            (cache_dir / ".vale.ini").write_text("StylesPath = styles\nPackages = Google\n", encoding="utf-8")

            result = ensure_builtin_vale_config(cache_dir, template_ini, run=fake_run)

            self.assertEqual(result, cache_dir / ".vale.ini")
            self.assertEqual(calls, [])


class CheckProseTests(unittest.TestCase):
    def test_skips_without_failing_when_unavailable(self):
        result = check_prose("doc.md", config_path="x.ini", which=_which_only())

        self.assertFalse(result["ran"])
        self.assertTrue(result["passed"])

    def test_reports_findings_from_a_normal_run(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 0
                stdout = json.dumps({
                    "doc.md": [
                        {
                            "Line": 3,
                            "Message": "Use 'to' instead of 'In order to'.",
                            "Check": "Google.WordListCase",
                            "Severity": "warning",
                        }
                    ]
                })
                stderr = ""

            return R()

        result = check_prose("doc.md", config_path="x.ini", which=_which_only("vale"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["Check"], "Google.WordListCase")

    def test_passes_when_there_are_no_findings(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 0
                stdout = json.dumps({})
                stderr = ""

            return R()

        result = check_prose("doc.md", config_path="x.ini", which=_which_only("vale"), run=fake_run)

        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_passes_when_vale_reports_no_findings_as_a_bare_list(self):
        """Confirmed live: vale's "no findings" JSON is {} for a single
        clean file but [] when multiple files were checked and all are
        clean -- a real shape inconsistency, not a hypothetical one."""
        def fake_run(args, **kwargs):
            class R:
                returncode = 0
                stdout = json.dumps([])
                stderr = ""

            return R()

        result = check_prose("doc.md", config_path="x.ini", which=_which_only("vale"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_a_tool_level_error_like_a_missing_config_is_reported_as_not_passed(self):
        def fake_run(args, **kwargs):
            class R:
                returncode = 2
                stdout = json.dumps({"Line": 0, "Path": "", "Text": "no config file found", "Code": "E100"})
                stderr = ""

            return R()

        result = check_prose("doc.md", config_path="x.ini", which=_which_only("vale"), run=fake_run)

        self.assertTrue(result["ran"])
        self.assertFalse(result["passed"])
        self.assertIn("no config file found", result["output"])

    def test_passes_the_config_path_through(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class R:
                returncode = 0
                stdout = json.dumps({})
                stderr = ""

            return R()

        check_prose("doc.md", config_path="x.ini", which=_which_only("vale"), run=fake_run)

        self.assertEqual(calls, [["vale", "--output=JSON", "--config", "x.ini", "doc.md"]])

    def test_accepts_several_paths_in_one_invocation(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

            class R:
                returncode = 0
                stdout = json.dumps({})
                stderr = ""

            return R()

        check_prose(["a.md", "b.md"], config_path="x.ini", which=_which_only("vale"), run=fake_run)

        self.assertEqual(calls, [["vale", "--output=JSON", "--config", "x.ini", "a.md", "b.md"]])


@unittest.skipUnless(shutil.which("vale"), "vale is not installed in this environment")
class RealValeTests(unittest.TestCase):
    def test_syncing_and_checking_against_the_real_google_style(self):
        with tempfile.TemporaryDirectory() as config_dir:
            config_dir = Path(config_dir)
            ini_path = config_dir / ".vale.ini"
            ini_path.write_text(
                "StylesPath = styles\nMinAlertLevel = suggestion\nPackages = Google\n\n"
                "[*.md]\nBasedOnStyles = Google\n",
                encoding="utf-8",
            )

            synced = ensure_builtin_styles_synced(config_dir)
            if not synced:
                self.skipTest("vale sync failed (no network in this environment)")

            with tempfile.TemporaryDirectory() as doc_dir:
                doc_path = Path(doc_dir) / "doc.md"
                doc_path.write_text("# Test\n\nIn order to utilize this, you should click here.\n", encoding="utf-8")

                result = check_prose(str(doc_path), config_path=str(ini_path))

                self.assertTrue(result["ran"])
                self.assertFalse(result["passed"])
                self.assertTrue(any(f.get("Check", "").startswith("Google.") for f in result["findings"]))

    def test_multiple_clean_files_pass_despite_vales_list_shaped_json(self):
        with tempfile.TemporaryDirectory() as config_dir:
            config_dir = Path(config_dir)
            ini_path = config_dir / ".vale.ini"
            ini_path.write_text(
                "StylesPath = styles\nMinAlertLevel = suggestion\nPackages = Google\n\n"
                "[*.md]\nBasedOnStyles = Google\n",
                encoding="utf-8",
            )

            synced = ensure_builtin_styles_synced(config_dir)
            if not synced:
                self.skipTest("vale sync failed (no network in this environment)")

            with tempfile.TemporaryDirectory() as doc_dir:
                doc_dir = Path(doc_dir)
                (doc_dir / "a.md").write_text("# A\n", encoding="utf-8")
                (doc_dir / "b.md").write_text("# B\n", encoding="utf-8")

                result = check_prose([str(doc_dir / "a.md"), str(doc_dir / "b.md")], config_path=str(ini_path))

                self.assertTrue(result["ran"])
                self.assertTrue(result["passed"])
                self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
