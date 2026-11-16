"""Tests for the gh-api inspection layer. Every subprocess call is faked --
these tests never touch live GitHub; they verify the right `gh api` path
gets requested and the right fields get extracted from a realistic fixture
response (the branch-rules fixtures mirror real shapes confirmed live
against actions/checkout's and CtrlCarlitos/skills' actual branches).

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.inspect import (
    inspect_branch_rules,
    inspect_bypass_actors,
    inspect_files,
    inspect_repo_settings,
    inspect_tag_protection,
)


class _FakeCompletedProcess:
    def __init__(self, stdout):
        self.stdout = stdout


class InspectRepoSettingsTests(unittest.TestCase):
    def test_requests_the_right_gh_api_path(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return _FakeCompletedProcess(json.dumps({
                "default_branch": "main",
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "delete_branch_on_merge": True,
            }))

        inspect_repo_settings("acme", "widgets", run=fake_run)

        self.assertEqual(calls[0][:2], ["gh", "api"])
        self.assertIn("repos/acme/widgets", calls[0])

    def test_normalizes_the_merge_strategy_flags(self):
        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps({
                "default_branch": "main",
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "delete_branch_on_merge": True,
            }))

        result = inspect_repo_settings("acme", "widgets", run=fake_run)

        self.assertEqual(result["default_branch"], "main")
        self.assertEqual(result["merge_strategy"], "squash_only")
        self.assertTrue(result["delete_branch_on_merge"])

    def test_reads_whether_auto_merge_is_allowed(self):
        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps({"default_branch": "main", "allow_auto_merge": True}))

        self.assertTrue(inspect_repo_settings("acme", "widgets", run=fake_run)["allow_auto_merge"])

        def fake_run_absent(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps({"default_branch": "main"}))

        self.assertFalse(inspect_repo_settings("acme", "widgets", run=fake_run_absent)["allow_auto_merge"])


class InspectBranchRulesTests(unittest.TestCase):
    def test_extracts_pull_request_and_status_check_parameters(self):
        # Shape confirmed live via `gh api repos/actions/checkout/rules/branches/main`.
        fixture = [
            {"type": "deletion", "ruleset_source_type": "Organization"},
            {"type": "non_fast_forward", "ruleset_source_type": "Organization"},
            {"type": "required_linear_history", "ruleset_source_type": "Organization"},
            {"type": "required_signatures", "ruleset_source_type": "Organization"},
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "required_review_thread_resolution": True,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": "build"}, {"context": "test"}]},
            },
        ]

        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps(fixture))

        result = inspect_branch_rules("acme", "widgets", "main", run=fake_run)

        self.assertTrue(result["require_pull_request"])
        self.assertTrue(result["required_review_thread_resolution"])
        self.assertTrue(result["required_signatures"])
        self.assertTrue(result["required_linear_history"])
        self.assertTrue(result["block_force_push"])
        self.assertTrue(result["block_branch_deletion"])
        self.assertEqual(result["required_status_checks"], ["build", "test"])

    def test_reports_absence_when_the_effective_rule_list_is_empty(self):
        # Real behavior confirmed live: `gh api repos/CtrlCarlitos/skills/rules/branches/main`
        # returns "[]" -- no classic protection and no applicable ruleset.
        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess("[]")

        result = inspect_branch_rules("acme", "widgets", "main", run=fake_run)

        self.assertFalse(result["require_pull_request"])
        self.assertFalse(result["block_force_push"])
        self.assertFalse(result["block_branch_deletion"])
        self.assertEqual(result["required_status_checks"], [])
        self.assertFalse(result["strict_required_status_checks"])
        self.assertEqual(result["ruleset_refs"], [])

    def test_reads_up_to_date_and_which_rulesets_the_rules_come_from(self):
        # Shape confirmed live via `gh api repos/CtrlCarlitos/dotfiles/rules/branches/main` (2026-11-16).
        source = {"ruleset_source_type": "Repository", "ruleset_source": "acme/widgets", "ruleset_id": 7}
        fixture = [
            {"type": "deletion", **source},
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [{"context": "build"}],
                    "strict_required_status_checks_policy": True,
                },
                **source,
            },
            {"type": "non_fast_forward", "ruleset_source_type": "Organization", "ruleset_source": "acme", "ruleset_id": 9},
        ]

        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps(fixture))

        result = inspect_branch_rules("acme", "widgets", "main", run=fake_run)

        self.assertTrue(result["strict_required_status_checks"])
        self.assertEqual(result["ruleset_refs"], [
            {"source_type": "Repository", "source": "acme/widgets", "id": 7},
            {"source_type": "Organization", "source": "acme", "id": 9},
        ])


class InspectBypassActorsTests(unittest.TestCase):
    def test_no_rulesets_means_nothing_to_bypass(self):
        def fake_run(cmd, **kwargs):
            raise AssertionError("no ruleset means no API call")

        self.assertEqual(inspect_bypass_actors([], run=fake_run), {"no_bypass_actors": True, "bypass_actors": []})

    def test_reads_each_ruleset_from_its_own_endpoint(self):
        # Shape confirmed live via `gh api repos/CtrlCarlitos/dotfiles/rulesets/23142280` (2026-11-16).
        calls = []
        by_path = {
            "repos/acme/widgets/rulesets/7": {"id": 7, "bypass_actors": []},
            "orgs/acme/rulesets/9": {
                "id": 9,
                "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
            },
        }

        def fake_run(cmd, **kwargs):
            calls.append(cmd[-1])
            return _FakeCompletedProcess(json.dumps(by_path[cmd[-1]]))

        refs = [
            {"source_type": "Repository", "source": "acme/widgets", "id": 7},
            {"source_type": "Organization", "source": "acme", "id": 9},
        ]
        result = inspect_bypass_actors(refs, run=fake_run)

        self.assertEqual(calls, ["repos/acme/widgets/rulesets/7", "orgs/acme/rulesets/9"])
        self.assertFalse(result["no_bypass_actors"])
        self.assertEqual(result["bypass_actors"], ["RepositoryRole 5 (always) in ruleset 9"])

    def test_empty_bypass_lists_everywhere_mean_no_bypass(self):
        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps({"id": 7, "bypass_actors": []}))

        result = inspect_bypass_actors([{"source_type": "Repository", "source": "acme/widgets", "id": 7}], run=fake_run)

        self.assertTrue(result["no_bypass_actors"])


class InspectTagProtectionTests(unittest.TestCase):
    def test_no_rulesets_means_unprotected(self):
        # Real behavior confirmed live: `gh api repos/CtrlCarlitos/skills/rulesets` returns "[]".
        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess("[]")

        result = inspect_tag_protection("acme", "widgets", run=fake_run)

        self.assertFalse(result["release_tags_protected"])

    def test_an_active_tag_targeted_ruleset_means_protected(self):
        fixture = [
            {"id": 1, "name": "protect-releases", "target": "tag", "enforcement": "active"},
        ]

        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps(fixture))

        result = inspect_tag_protection("acme", "widgets", run=fake_run)

        self.assertTrue(result["release_tags_protected"])

    def test_a_disabled_tag_ruleset_does_not_count(self):
        fixture = [
            {"id": 1, "name": "draft-rule", "target": "tag", "enforcement": "disabled"},
        ]

        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps(fixture))

        result = inspect_tag_protection("acme", "widgets", run=fake_run)

        self.assertFalse(result["release_tags_protected"])

    def test_a_branch_targeted_ruleset_does_not_count_as_tag_protection(self):
        fixture = [
            {"id": 1, "name": "protect-main", "target": "branch", "enforcement": "active"},
        ]

        def fake_run(cmd, **kwargs):
            return _FakeCompletedProcess(json.dumps(fixture))

        result = inspect_tag_protection("acme", "widgets", run=fake_run)

        self.assertFalse(result["release_tags_protected"])


class InspectFilesTests(unittest.TestCase):
    def test_reports_present_when_any_candidate_path_exists(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / ".github").mkdir()
            (root / ".github" / "CODEOWNERS").write_text("* @someone\n", encoding="utf-8")

            result = inspect_files(root, {"codeowners": ["CODEOWNERS", ".github/CODEOWNERS"]})

            self.assertTrue(result["codeowners"])

    def test_reports_missing_when_no_candidate_path_exists(self):
        with tempfile.TemporaryDirectory() as root:
            result = inspect_files(Path(root), {"codeowners": ["CODEOWNERS", ".github/CODEOWNERS"]})

            self.assertFalse(result["codeowners"])


if __name__ == "__main__":
    unittest.main()
