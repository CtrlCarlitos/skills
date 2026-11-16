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

    def test_finds_a_manifest_in_a_subdirectory(self):
        """CtrlCarlitos/skills keeps its requirements.txt files per skill
        (skills/<name>/requirements.txt), none at the root."""
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "skills" / "deliver").mkdir(parents=True)
            (Path(root) / "skills" / "deliver" / "requirements.txt").write_text("", encoding="utf-8")

            self.assertTrue(has_a_dependency_manifest(Path(root)))

    def test_github_actions_workflows_count(self):
        """Dependabot updates the actions a workflow uses (its
        github-actions ecosystem), so a repo with workflows has something
        for it to do even with no package manifest."""
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".github" / "workflows").mkdir(parents=True)
            (Path(root) / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")

            self.assertTrue(has_a_dependency_manifest(Path(root)))

    def test_ignores_manifests_in_tool_and_dependency_directories(self):
        """Copies under node_modules/, a virtualenv, .git/, or Claude Code's
        own .claude/worktrees/ are not the repo's dependencies."""
        for parts in (
            ("node_modules", "left-pad", "package.json"),
            (".venv", "lib", "pyproject.toml"),
            (".claude", "worktrees", "wt1", "package.json"),
            (".git", "modules", "x", "go.mod"),
        ):
            with tempfile.TemporaryDirectory() as root:
                path = Path(root).joinpath(*parts)
                path.parent.mkdir(parents=True)
                path.write_text("", encoding="utf-8")

                self.assertFalse(has_a_dependency_manifest(Path(root)), f"should ignore {'/'.join(parts)}")


class LooksAgenticTests(unittest.TestCase):
    def test_true_when_claude_md_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "CLAUDE.md").write_text("", encoding="utf-8")

            self.assertTrue(looks_agentic(Path(root)))

    def test_true_when_claude_settings_json_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".claude").mkdir()
            (Path(root) / ".claude" / "settings.json").write_text("{}", encoding="utf-8")

            self.assertTrue(looks_agentic(Path(root)))

    def test_true_when_claude_commands_dir_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".claude" / "commands").mkdir(parents=True)

            self.assertTrue(looks_agentic(Path(root)))

    def test_true_when_cursor_rules_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".cursor" / "rules").mkdir(parents=True)

            self.assertTrue(looks_agentic(Path(root)))

    def test_true_when_copilot_instructions_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".github").mkdir()
            (Path(root) / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")

            self.assertTrue(looks_agentic(Path(root)))

    def test_false_for_a_plain_repo_with_none_of_these_markers(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(looks_agentic(Path(root)))

    def test_false_when_the_claude_dir_only_holds_incidental_worktree_state(self):
        """Regression: a bare .claude/ directory is not a reliable signal --
        Claude Code's own worktree-isolation feature creates .claude/worktrees/
        automatically just from using it, regardless of whether the repo's
        maintainers ever deliberately adopted any AI-agent tooling. Confirmed
        live: CtrlCarlitos/skills' own .claude/ contains nothing but
        worktrees/, created by this very session, not by a maintainer.
        """
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".claude" / "worktrees").mkdir(parents=True)

            self.assertFalse(looks_agentic(Path(root)))


if __name__ == "__main__":
    unittest.main()
