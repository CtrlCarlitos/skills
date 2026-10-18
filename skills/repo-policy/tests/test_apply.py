"""Tests for the itemized apply layer. build_branch_ruleset_body is pure
and fully tested directly; the subprocess-calling wrappers are tested by
injecting a fake `run` -- never touching live GitHub or a real repo.

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import json
import unittest

from scripts.apply import apply_branch_ruleset, apply_repo_settings, build_branch_ruleset_body


class BuildBranchRulesetBodyTests(unittest.TestCase):
    def test_empty_policy_produces_no_rules(self):
        body = build_branch_ruleset_body({})

        self.assertEqual(body["rules"], [])
        self.assertEqual(body["target"], "branch")
        self.assertEqual(body["enforcement"], "active")

    def test_require_pull_request_adds_a_pull_request_rule_with_its_parameters(self):
        policy = {
            "require_pull_request": True,
            "required_approving_review_count": 2,
            "require_code_owner_review": True,
            "required_review_thread_resolution": True,
        }

        body = build_branch_ruleset_body(policy)

        pr_rules = [r for r in body["rules"] if r["type"] == "pull_request"]
        self.assertEqual(len(pr_rules), 1)
        self.assertEqual(pr_rules[0]["parameters"]["required_approving_review_count"], 2)
        self.assertTrue(pr_rules[0]["parameters"]["require_code_owner_review"])
        self.assertTrue(pr_rules[0]["parameters"]["required_review_thread_resolution"])

    def test_required_status_checks_become_context_objects(self):
        policy = {"required_status_checks": ["build", "test"]}

        body = build_branch_ruleset_body(policy)

        status_rules = [r for r in body["rules"] if r["type"] == "required_status_checks"]
        self.assertEqual(
            status_rules[0]["parameters"]["required_status_checks"],
            [{"context": "build"}, {"context": "test"}],
        )

    def test_boolean_flags_map_to_their_bare_rule_types(self):
        policy = {
            "required_signatures": True,
            "required_linear_history": True,
            "block_force_push": True,
            "block_branch_deletion": True,
        }

        body = build_branch_ruleset_body(policy)

        rule_types = {r["type"] for r in body["rules"]}
        self.assertEqual(rule_types, {"required_signatures", "required_linear_history", "non_fast_forward", "deletion"})

    def test_targets_the_default_branch_placeholder_unless_given_a_pattern(self):
        body = build_branch_ruleset_body({})

        self.assertEqual(body["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])


class ApplyRepoSettingsTests(unittest.TestCase):
    def test_sends_a_patch_with_only_the_requested_changes(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs.get("input")))
            return None

        apply_repo_settings("acme", "widgets", {"delete_branch_on_merge": True}, run=fake_run)

        cmd, body_json = calls[0]
        self.assertEqual(cmd[:4], ["gh", "api", "-X", "PATCH"])
        self.assertIn("repos/acme/widgets", cmd)
        self.assertEqual(json.loads(body_json), {"delete_branch_on_merge": True})

    def test_merge_strategy_squash_only_sets_exactly_one_flag_true(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(kwargs.get("input"))
            return None

        apply_repo_settings("acme", "widgets", {"merge_strategy": "squash_only"}, run=fake_run)

        body = json.loads(calls[0])
        self.assertEqual(body["allow_squash_merge"], True)
        self.assertEqual(body["allow_merge_commit"], False)
        self.assertEqual(body["allow_rebase_merge"], False)

    def test_no_requested_changes_makes_no_call_at_all(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)

        apply_repo_settings("acme", "widgets", {}, run=fake_run)

        self.assertEqual(calls, [])


class ApplyBranchRulesetTests(unittest.TestCase):
    def test_posts_the_given_ruleset_body_to_the_rulesets_endpoint(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs.get("input")))

        body = {"name": "x", "target": "branch", "enforcement": "active", "conditions": {}, "rules": []}
        apply_branch_ruleset("acme", "widgets", body, run=fake_run)

        cmd, sent_body = calls[0]
        self.assertEqual(cmd[:4], ["gh", "api", "-X", "POST"])
        self.assertIn("repos/acme/widgets/rulesets", cmd)
        self.assertEqual(json.loads(sent_body), body)


if __name__ == "__main__":
    unittest.main()
