"""Tests for "required where applicable" detection (currently just
Dependabot: only a gap if the repo has a package manifest Dependabot
could actually update).

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from scripts.applicability import has_a_dependency_manifest, looks_agentic


class HasADependencyManifestTests(unittest.TestCase):
    def test_true_when_a_recognized_manifest_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "package.json").write_text("{}", encoding="utf-8")

            self.assertTrue(has_a_dependency_manifest(Path(root)))

    def test_false_when_no_recognized_manifest_exists(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(has_a_dependency_manifest(Path(root)))

    def test_recognizes_several_common_ecosystems(self):
        for manifest in ("go.mod", "Cargo.toml", "Gemfile", "requirements.txt", "composer.json", "pom.xml"):
            with tempfile.TemporaryDirectory() as root:
                (Path(root) / manifest).write_text("", encoding="utf-8")

                self.assertTrue(has_a_dependency_manifest(Path(root)), f"should detect {manifest}")


class LooksAgenticTests(unittest.TestCase):
    def test_true_when_a_claude_config_dir_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".claude").mkdir()

            self.assertTrue(looks_agentic(Path(root)))

    def test_true_when_claude_md_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "CLAUDE.md").write_text("", encoding="utf-8")

            self.assertTrue(looks_agentic(Path(root)))

    def test_true_when_a_cursor_config_dir_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".cursor").mkdir()

            self.assertTrue(looks_agentic(Path(root)))

    def test_false_for_a_plain_repo_with_none_of_these_markers(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(looks_agentic(Path(root)))


if __name__ == "__main__":
    unittest.main()
