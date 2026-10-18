"""Tests for the policy lookup chain: repo override -> named user policy ->
built-in default. Mirrors the lookup convention release-notes/update-docs
already use in this repo.

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from scripts.policy import load_policy

BUILTIN = {"delete_branch_on_merge": True}


class LoadPolicyTests(unittest.TestCase):
    def test_falls_back_to_builtin_when_nothing_else_exists(self):
        with tempfile.TemporaryDirectory() as repo_root, tempfile.TemporaryDirectory() as home:
            policy, source = load_policy(Path(repo_root), Path(home), BUILTIN)

            self.assertEqual(policy, BUILTIN)
            self.assertIn("built-in", source)

    def test_uses_the_named_user_policy_when_present(self):
        with tempfile.TemporaryDirectory() as repo_root, tempfile.TemporaryDirectory() as home:
            user_policy_dir = Path(home) / ".config" / "repo-policy" / "policies"
            user_policy_dir.mkdir(parents=True)
            (user_policy_dir / "default.yaml").write_text("delete_branch_on_merge: false\n", encoding="utf-8")

            policy, source = load_policy(Path(repo_root), Path(home), BUILTIN)

            self.assertEqual(policy, {"delete_branch_on_merge": False})
            self.assertIn("user policy", source)

    def test_repo_override_wins_over_the_user_policy(self):
        with tempfile.TemporaryDirectory() as repo_root, tempfile.TemporaryDirectory() as home:
            user_policy_dir = Path(home) / ".config" / "repo-policy" / "policies"
            user_policy_dir.mkdir(parents=True)
            (user_policy_dir / "default.yaml").write_text("delete_branch_on_merge: false\n", encoding="utf-8")

            repo_policy_dir = Path(repo_root) / ".repo-policy"
            repo_policy_dir.mkdir(parents=True)
            (repo_policy_dir / "policy.yaml").write_text("delete_branch_on_merge: true\n", encoding="utf-8")

            policy, source = load_policy(Path(repo_root), Path(home), BUILTIN)

            self.assertEqual(policy, {"delete_branch_on_merge": True})
            self.assertIn("repo override", source)

    def test_a_different_named_policy_can_be_requested_explicitly(self):
        with tempfile.TemporaryDirectory() as repo_root, tempfile.TemporaryDirectory() as home:
            user_policy_dir = Path(home) / ".config" / "repo-policy" / "policies"
            user_policy_dir.mkdir(parents=True)
            (user_policy_dir / "strict.yaml").write_text("delete_branch_on_merge: true\n", encoding="utf-8")

            policy, source = load_policy(Path(repo_root), Path(home), BUILTIN, policy_name="strict")

            self.assertEqual(policy, {"delete_branch_on_merge": True})


if __name__ == "__main__":
    unittest.main()
