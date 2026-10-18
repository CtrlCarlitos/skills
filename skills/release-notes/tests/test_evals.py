"""Executes every fixture in evals/evals.json against the real modules --
this is the integration layer the issue's deliverable list asks for: real
git histories covering a revert, a breaking change mislabelled as a
refactor, a squash merge, a no-visible-change range, a missing tag, a
shallow clone, one fixture per built-in repo type, a repo-level
.release-notes/ override, and output that passes markdownlint.

Run from skills/release-notes/: python3 -m unittest discover -s tests
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_fixture import build_fixture
from scripts.commits import collapse_reverted_pairs, extract_pr_reference, list_commits
from scripts.lint import lint_file
from scripts.range import RangeError, resolve_range
from scripts.render import render_release_section
from scripts.repo_type import detect_type, resolve_type_guide

EVALS_PATH = Path(__file__).resolve().parent.parent / "evals" / "evals.json"
BUILTIN_TYPES_DIR = Path(__file__).resolve().parent.parent / "references"
LINT_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.jsonc"


def _load_fixtures() -> dict:
    fixtures = json.loads(EVALS_PATH.read_text(encoding="utf-8"))["fixtures"]
    return {f["id"]: f for f in fixtures}


def _make_shallow_clone(source_root: Path, clone_parent: Path) -> Path:
    clone_root = clone_parent / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{source_root}", str(clone_root)],
        cwd=clone_parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return clone_root


class RevertInRangeTests(unittest.TestCase):
    def test_a_reverted_feature_and_its_revert_are_both_excluded(self):
        fixture = _load_fixtures()["revert-in-range"]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            build_fixture(fixture["ops"], root)

            commits = list_commits(root, base=fixture["base"], head=fixture["head"])
            kept, not_included = collapse_reverted_pairs(commits)

            self.assertEqual([c["subject"] for c in kept], fixture["expect_kept_subjects"])
            self.assertEqual(
                {c["subject"] for c in not_included}, set(fixture["expect_not_included_subjects"])
            )


class BreakingChangeLabelledRefactorTests(unittest.TestCase):
    def test_the_mislabelled_commit_is_kept_for_the_agent_to_read_its_diff(self):
        fixture = _load_fixtures()["breaking-change-labelled-refactor"]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            build_fixture(fixture["ops"], root)

            commits = list_commits(root, base=fixture["base"], head=fixture["head"])
            kept, _ = collapse_reverted_pairs(commits)

            self.assertEqual([c["subject"] for c in kept], fixture["expect_kept_subjects"])

            diff = subprocess.run(
                ["git", "show", kept[0]["sha"]], cwd=root, capture_output=True, text=True, check=True
            ).stdout
            self.assertIn(fixture["expect_diff_removes"], diff)
            self.assertIn("-def parse_config_legacy", diff)


class SquashMergeTests(unittest.TestCase):
    def test_the_pr_reference_is_extracted_from_the_squash_merge_subject(self):
        fixture = _load_fixtures()["squash-merge"]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            build_fixture(fixture["ops"], root)

            commits = list_commits(root, base=fixture["base"], head=fixture["head"])
            kept, _ = collapse_reverted_pairs(commits)

            self.assertEqual([c["subject"] for c in kept], fixture["expect_kept_subjects"])
            self.assertEqual(extract_pr_reference(kept[0]), fixture["expect_pr_reference"])


class NoUserVisibleChangeTests(unittest.TestCase):
    def test_rendering_an_empty_sections_mapping_omits_every_section(self):
        fixture = _load_fixtures()["no-user-visible-change"]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            build_fixture(fixture["ops"], root)

            commits = list_commits(root, base=fixture["base"], head=fixture["head"])
            kept, _ = collapse_reverted_pairs(commits)
            self.assertEqual([c["subject"] for c in kept], fixture["expect_kept_subjects"])

            result = render_release_section("Unreleased", "2026-02-01", fixture["expect_rendered_sections"])

            self.assertNotIn("###", result)


class MissingTagOrShallowCloneTests(unittest.TestCase):
    def test_missing_tag_raises_range_error(self):
        fixture = _load_fixtures()["missing-tag"]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            build_fixture(fixture["ops"], root)

            with self.assertRaises(RangeError) as ctx:
                resolve_range(root)
            self.assertIn(fixture["expect_range_error_contains"], str(ctx.exception).lower())

    def test_shallow_clone_raises_range_error(self):
        fixture = _load_fixtures()["shallow-clone"]
        with tempfile.TemporaryDirectory() as source_root, tempfile.TemporaryDirectory() as clone_parent:
            source_root, clone_parent = Path(source_root), Path(clone_parent)
            build_fixture(fixture["ops"], source_root)
            clone_root = _make_shallow_clone(source_root, clone_parent)

            with self.assertRaises(RangeError) as ctx:
                resolve_range(clone_root)
            self.assertIn(fixture["expect_range_error_contains"], str(ctx.exception).lower())


class RepoTypeFixtureTests(unittest.TestCase):
    def test_each_detectable_type_fixture_is_detected_correctly(self):
        fixtures = _load_fixtures()
        for fixture_id in ("repo-type-odoo", "repo-type-phoenix", "repo-type-go", "repo-type-flutter", "repo-type-generic"):
            fixture = fixtures[fixture_id]
            with self.subTest(fixture_id=fixture_id), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                build_fixture(fixture["ops"], root)

                self.assertEqual(detect_type(root), fixture["expect_detected_type"])

    def test_course_and_docs_are_only_reached_by_an_explicit_type_name(self):
        fixtures = _load_fixtures()
        for fixture_id in ("repo-type-course", "repo-type-docs"):
            fixture = fixtures[fixture_id]
            with self.subTest(fixture_id=fixture_id), tempfile.TemporaryDirectory() as root, \
                    tempfile.TemporaryDirectory() as home:
                root, home = Path(root), Path(home)
                build_fixture(fixture["ops"], root)
                # No detection signature: auto-detection would say "generic", not this type.
                self.assertEqual(detect_type(root), "generic")

                guide, _source = resolve_type_guide(
                    root, home, BUILTIN_TYPES_DIR, type_name=fixture["explicit_type_name"]
                )
                self.assertIn(fixture["expect_guide_contains"], guide)


class RepoOverrideTests(unittest.TestCase):
    def test_a_repo_release_notes_override_wins_over_auto_detected_go(self):
        fixture = _load_fixtures()["repo-with-release-notes-override"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)
            self.assertEqual(detect_type(root), "go")  # would auto-detect as go without the override

            guide, source = resolve_type_guide(root, home, BUILTIN_TYPES_DIR)

            self.assertIn(fixture["expect_guide_contains"], guide)
            self.assertIn("repo override", source)


class MarkdownlintFixtureTests(unittest.TestCase):
    def test_a_realistic_rendered_section_passes_markdownlint(self):
        fixture = _load_fixtures()["output-passes-markdownlint"]
        rendered = render_release_section(
            fixture["version"],
            fixture["date"],
            fixture["sections"],
            range_text=fixture["range_text"],
            commit_count=fixture["commit_count"],
            pr_count=fixture["pr_count"],
            audience=fixture["audience"],
        )

        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "CHANGELOG.md"
            path.write_text(f"# Changelog\n\n{rendered}", encoding="utf-8")

            result = lint_file(str(path), config_path=str(LINT_CONFIG))

            if result["ran"]:
                self.assertTrue(result["passed"], result["output"])
            else:
                self.skipTest("markdownlint-cli2 not available in this environment")


if __name__ == "__main__":
    unittest.main()
