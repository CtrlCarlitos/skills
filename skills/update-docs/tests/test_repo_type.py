"""Tests for repo-type detection and the type-guide lookup chain (repo
override -> user config -> built-in), mirroring release-notes/scripts/
repo_type.py's convention (itself mirroring repo-policy's policy.py).
Uses real tmp directories and real files, not mocks -- this is about real
filesystem lookup order, not business logic worth mocking.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from scripts.repo_type import detect_type, resolve_type_guide


class DetectTypeTests(unittest.TestCase):
    def test_detects_odoo_from_a_manifest_file(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "__manifest__.py").write_text("{'name': 'x'}", encoding="utf-8")

            self.assertEqual(detect_type(root), "odoo")

    def test_detects_go_from_a_go_mod_file(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "go.mod").write_text("module example.com/x\n", encoding="utf-8")

            self.assertEqual(detect_type(root), "go")

    def test_detects_flutter_from_a_pubspec_with_the_flutter_sdk(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "pubspec.yaml").write_text(
                "name: x\ndependencies:\n  flutter:\n    sdk: flutter\n", encoding="utf-8"
            )

            self.assertEqual(detect_type(root), "flutter")

    def test_a_bare_pubspec_without_the_flutter_sdk_is_not_flutter(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "pubspec.yaml").write_text("name: x\ndependencies:\n  path: x\n", encoding="utf-8")

            self.assertEqual(detect_type(root), "generic")

    def test_detects_phoenix_from_a_mix_exs_depending_on_phoenix(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "mix.exs").write_text(
                "defmodule X.MixProject do\n  defp deps do\n    [{:phoenix, \"~> 1.7\"}]\n  end\nend\n",
                encoding="utf-8",
            )

            self.assertEqual(detect_type(root), "phoenix")

    def test_a_bare_mix_exs_without_phoenix_is_not_phoenix(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "mix.exs").write_text("defmodule X.MixProject do\nend\n", encoding="utf-8")

            self.assertEqual(detect_type(root), "generic")

    def test_falls_back_to_generic_when_nothing_matches(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)

            self.assertEqual(detect_type(root), "generic")


class ResolveTypeGuideTests(unittest.TestCase):
    def test_a_repo_override_wins_regardless_of_detected_type(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            override_dir = root / ".update-docs"
            override_dir.mkdir()
            (override_dir / "type.md").write_text("# repo-specific guide\n", encoding="utf-8")
            (builtin_dir / "generic.md").write_text("# builtin generic\n", encoding="utf-8")

            guide, source = resolve_type_guide(root, home, builtin_dir)

            self.assertEqual(guide, "# repo-specific guide\n")
            self.assertIn("repo override", source)

    def test_a_user_config_type_file_is_used_when_no_repo_override_exists(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            user_types_dir = home / ".config" / "update-docs" / "types"
            user_types_dir.mkdir(parents=True)
            (user_types_dir / "go.md").write_text("# user go guide\n", encoding="utf-8")
            (builtin_dir / "go.md").write_text("# builtin go\n", encoding="utf-8")

            guide, source = resolve_type_guide(root, home, builtin_dir, type_name="go")

            self.assertEqual(guide, "# user go guide\n")
            self.assertIn("user", source)

    def test_falls_back_to_the_builtin_guide_when_nothing_else_overrides_it(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            (builtin_dir / "generic.md").write_text("# builtin generic\n", encoding="utf-8")

            guide, source = resolve_type_guide(root, home, builtin_dir, type_name="generic")

            self.assertEqual(guide, "# builtin generic\n")
            self.assertIn("built-in", source)

    def test_uses_the_detected_type_when_no_type_name_is_given(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            (root / "go.mod").write_text("module example.com/x\n", encoding="utf-8")
            (builtin_dir / "go.md").write_text("# builtin go\n", encoding="utf-8")

            guide, source = resolve_type_guide(root, home, builtin_dir)

            self.assertEqual(guide, "# builtin go\n")

    def test_raises_a_clear_error_when_no_guide_exists_anywhere_for_the_type(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)

            with self.assertRaises(FileNotFoundError) as ctx:
                resolve_type_guide(root, home, builtin_dir, type_name="course")

            self.assertIn("course", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
