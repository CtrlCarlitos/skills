"""Tests for the audit orchestration layer: merging the four inspectors'
output into one current-state dict. Each inspector is faked -- this test
never calls gh or touches the filesystem beyond what inspect_files already
covers on its own (tested separately in test_inspect.py).

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

from scripts.audit import gather_current_state


class GatherCurrentStateTests(unittest.TestCase):
    def test_merges_all_four_inspectors_into_one_dict(self):
        def fake_repo_settings(owner, repo):
            return {"default_branch": "main", "merge_strategy": "squash_only", "delete_branch_on_merge": True}

        def fake_branch_rules(owner, repo, branch):
            self.assertEqual(branch, "main")  # uses the default branch just inspected
            return {"require_pull_request": True, "block_force_push": True}

        def fake_tag_protection(owner, repo):
            return {"release_tags_protected": False}

        def fake_files(repo_root, candidates):
            return {"codeowners": True}

        result = gather_current_state(
            "acme", "widgets", Path("/tmp/not-used"), {"codeowners": ["CODEOWNERS"]},
            inspect_repo_settings_fn=fake_repo_settings,
            inspect_branch_rules_fn=fake_branch_rules,
            inspect_tag_protection_fn=fake_tag_protection,
            inspect_files_fn=fake_files,
        )

        self.assertEqual(result, {
            "default_branch": "main",
            "merge_strategy": "squash_only",
            "delete_branch_on_merge": True,
            "require_pull_request": True,
            "block_force_push": True,
            "require_status_checks": False,
            "no_bypass_actors": True,
            "bypass_actors": [],
            "release_tags_protected": False,
            "codeowners": True,
        })

    def test_reads_bypass_actors_from_the_rulesets_behind_the_branch_and_derives_any_required_ci(self):
        refs = [{"source_type": "Repository", "source": "acme/widgets", "id": 7}]
        seen = []

        def fake_bypass(ruleset_refs):
            seen.append(ruleset_refs)
            return {"no_bypass_actors": False, "bypass_actors": ["RepositoryRole 5 (always) in ruleset 7"]}

        result = gather_current_state(
            "acme", "widgets", Path("/tmp/not-used"), {},
            inspect_repo_settings_fn=lambda o, r: {"default_branch": "main"},
            inspect_branch_rules_fn=lambda o, r, b: {"required_status_checks": ["build"], "ruleset_refs": refs},
            inspect_tag_protection_fn=lambda o, r: {},
            inspect_files_fn=lambda root, c: {},
            inspect_bypass_actors_fn=fake_bypass,
        )

        self.assertEqual(seen, [refs])
        self.assertTrue(result["require_status_checks"])
        self.assertFalse(result["no_bypass_actors"])
        self.assertNotIn("ruleset_refs", result)


if __name__ == "__main__":
    unittest.main()
