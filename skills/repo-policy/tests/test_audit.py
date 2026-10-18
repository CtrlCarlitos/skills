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
            "release_tags_protected": False,
            "codeowners": True,
        })


if __name__ == "__main__":
    unittest.main()
