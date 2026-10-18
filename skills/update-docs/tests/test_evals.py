"""Executes every fixture in evals/evals.json against the real modules --
the issue's deliverable list asks for real git histories covering a
renamed flag still in the README, a generated README edited by hand, a
new undocumented env var, a doc describing a planned feature, an
accepted ADR that must not change, a repo with its own .update-docs/
override, and the audit mode leaving the repo unchanged.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_fixture import build_fixture
from scripts.gather import gather

EVALS_PATH = Path(__file__).resolve().parent.parent / "evals" / "evals.json"
BUILTIN_TYPES_DIR = Path(__file__).resolve().parent.parent / "references"


def _load_fixtures() -> dict:
    fixtures = json.loads(EVALS_PATH.read_text(encoding="utf-8"))["fixtures"]
    return {f["id"]: f for f in fixtures}


def _never_sync(cache_dir, template_path, run=None):
    return None


def _gather(root, fixture, home):
    return gather(
        root,
        scope=fixture["scope"],
        base=fixture.get("base"),
        home=home,
        builtin_types_dir=BUILTIN_TYPES_DIR,
        ensure_vale=_never_sync,
    )


class RenamedFlagStillInReadmeTests(unittest.TestCase):
    def test_the_unchanged_readme_is_in_all_doc_files_but_not_changed_doc_files(self):
        fixture = _load_fixtures()["renamed-flag-still-in-readme"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            result = _gather(root, fixture, home)

            self.assertEqual(result["changed_doc_files"], fixture["expect_changed_doc_files"])
            self.assertEqual(bool(fixture["expect_readme_in_all_doc_files"]), "README.md" in result["all_doc_files"])


class GeneratedReadmeEditedByHandTests(unittest.TestCase):
    def test_a_hand_edited_generated_readme_is_flagged(self):
        fixture = _load_fixtures()["generated-readme-edited-by-hand"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            result = _gather(root, fixture, home)

            self.assertEqual(result["changed_doc_files"], fixture["expect_changed_doc_files"])
            self.assertEqual(result["generated_docs"], fixture["expect_generated_docs"])


class NewEnvVarUndocumentedTests(unittest.TestCase):
    def test_the_code_change_is_visible_but_no_doc_is_in_scope(self):
        fixture = _load_fixtures()["new-env-var-undocumented"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            result = _gather(root, fixture, home)

            self.assertEqual(result["changed_doc_files"], fixture["expect_changed_doc_files"])
            self.assertIn(fixture["expect_changed_files_include"], result["changed_files"])


class DocDescribingPlannedFeatureTests(unittest.TestCase):
    def test_the_doc_is_discovered_normally_for_the_agent_to_read(self):
        fixture = _load_fixtures()["doc-describing-planned-feature"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            result = _gather(root, fixture, home)

            self.assertEqual(result["docs_in_scope"], fixture["expect_docs_in_scope"])


class AcceptedAdrNotTouchedTests(unittest.TestCase):
    def test_the_adr_never_appears_as_a_doc_to_audit(self):
        fixture = _load_fixtures()["accepted-adr-not-touched"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            result = _gather(root, fixture, home)

            self.assertEqual(result["changed_doc_files"], fixture["expect_changed_doc_files"])
            for key in fixture["expect_adr_excluded_from"]:
                self.assertNotIn("docs/adr/0001-use-postgres.md", result[key])


class RepoOverrideTests(unittest.TestCase):
    def test_the_repo_override_wins_over_auto_detected_go(self):
        fixture = _load_fixtures()["repo-with-own-update-docs-override"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            result = _gather(root, fixture, home)

            self.assertIn(fixture["expect_guide_contains"], result["repo_type"]["guide"])
            self.assertIn("repo override", result["repo_type"]["source"])


class AuditModeIsReadOnlyTests(unittest.TestCase):
    def test_gather_never_modifies_the_repo_being_audited(self):
        fixture = _load_fixtures()["audit-mode-leaves-the-repo-unchanged"]
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home:
            root, home = Path(root), Path(home)
            build_fixture(fixture["ops"], root)

            before = subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
            ).stdout
            before_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
            ).stdout

            _gather(root, fixture, home)

            after = subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
            ).stdout
            after_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
            ).stdout

            self.assertEqual(before, after)
            self.assertEqual(before_head, after_head)


if __name__ == "__main__":
    unittest.main()
