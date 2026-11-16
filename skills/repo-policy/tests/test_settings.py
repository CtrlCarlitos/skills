"""Tests for merge-strategy normalization and the settings registry.

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.settings import SETTINGS, merge_strategy_from_flags


class MergeStrategyFromFlagsTests(unittest.TestCase):
    def test_single_allowed_method_is_reported_as_only(self):
        flags = {"allow_squash_merge": True, "allow_merge_commit": False, "allow_rebase_merge": False}

        self.assertEqual(merge_strategy_from_flags(flags), "squash_only")

    def test_multiple_allowed_methods_is_any(self):
        flags = {"allow_squash_merge": True, "allow_merge_commit": True, "allow_rebase_merge": False}

        self.assertEqual(merge_strategy_from_flags(flags), "any")

    def test_no_allowed_methods_is_none(self):
        flags = {"allow_squash_merge": False, "allow_merge_commit": False, "allow_rebase_merge": False}

        self.assertEqual(merge_strategy_from_flags(flags), "none")


class SettingsRegistryTests(unittest.TestCase):
    def test_every_setting_has_a_unique_key(self):
        keys = [s.key for s in SETTINGS]

        self.assertEqual(len(keys), len(set(keys)), f"duplicate keys in SETTINGS: {keys}")

    def test_covers_every_row_in_the_issues_example_matrix(self):
        """Issue #5's example table lists these setting labels (not an
        exhaustive spec, but the registry should cover all of them)."""
        expected_labels = {
            "Default branch", "PR required", "Required CI",
            "Review threads resolved", "Signed commits", "Linear history",
            "Force push blocked", "Branch deletion blocked", "Merge strategy",
            "Delete merged branches", "Release tags protected", "CODEOWNERS",
            "CONTRIBUTING.md", "SECURITY.md", "PR template", "Issue templates",
            "Dependabot", "AGENTS.md",
        }
        actual_labels = {s.label for s in SETTINGS}

        missing = expected_labels - actual_labels
        self.assertEqual(missing, set(), f"SETTINGS is missing: {missing}")

    def test_covers_what_safe_autonomous_merging_depends_on(self):
        """#42: each of these decides whether an agent can merge without a
        person, or whether anyone can skip the checks. A policy key that is
        read but has no row (the approval count was one) is applied silently
        and never reported."""
        expected_keys = {
            "required_approving_review_count", "require_code_owner_review",
            "require_status_checks", "strict_required_status_checks",
            "allow_auto_merge", "no_bypass_actors",
        }
        actual_keys = {s.key for s in SETTINGS}

        missing = expected_keys - actual_keys
        self.assertEqual(missing, set(), f"SETTINGS is missing: {missing}")


class PresenceFormatTests(unittest.TestCase):
    def test_na_sentinel_is_not_mistaken_for_presence(self):
        dependabot_setting = next(s for s in SETTINGS if s.key == "dependabot")

        self.assertEqual(dependabot_setting.format("N/A"), "N/A")
        self.assertEqual(dependabot_setting.format(True), "Present")
        self.assertEqual(dependabot_setting.format(False), "Missing")


if __name__ == "__main__":
    unittest.main()
