"""Tests for the "not applicable" override: a setting that doesn't apply
to this repo (no dependency manifest for Dependabot, no agentic markers
for AGENTS.md) must report as N/A on both sides, never as a faked
"Present" match -- a user reading the matrix must not be misled into
thinking the file actually exists.

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

from scripts.audit import apply_not_applicable_overrides


class ApplyNotApplicableOverridesTests(unittest.TestCase):
    def test_dependabot_becomes_na_on_both_sides_when_no_manifest_exists(self):
        with tempfile.TemporaryDirectory() as root:
            current = {"dependabot": False}
            policy = {"dependabot": True}

            new_current, new_policy = apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(new_current["dependabot"], "N/A")
            self.assertEqual(new_policy["dependabot"], "N/A")

    def test_dependabot_is_left_alone_when_a_manifest_exists(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "package.json").write_text("{}", encoding="utf-8")
            current = {"dependabot": False}
            policy = {"dependabot": True}

            new_current, new_policy = apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(new_current["dependabot"], False)
            self.assertEqual(new_policy["dependabot"], True)

    def test_a_dependabot_config_that_exists_is_never_reported_as_na(self):
        """If a maintainer configured Dependabot, it applies by definition:
        reporting it N/A hid the real state of CtrlCarlitos/skills."""
        with tempfile.TemporaryDirectory() as root:
            current = {"dependabot": True}
            policy = {"dependabot": True}

            new_current, new_policy = apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(new_current["dependabot"], True)
            self.assertEqual(new_policy["dependabot"], True)

    def test_agents_md_becomes_na_on_both_sides_when_repo_is_not_agentic(self):
        with tempfile.TemporaryDirectory() as root:
            current = {"agents_md": False}
            policy = {"agents_md": True}

            new_current, new_policy = apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(new_current["agents_md"], "N/A")
            self.assertEqual(new_policy["agents_md"], "N/A")

    def test_an_empty_check_name_list_is_not_audited(self):
        """writing-a-policy.md: leave `required_status_checks` empty "to not
        audit CI check names at all". `require_status_checks` still catches a
        branch with no required check (#42)."""
        with tempfile.TemporaryDirectory() as root:
            current = {"required_status_checks": ["build"]}
            policy = {"required_status_checks": [], "require_status_checks": True}

            _, new_policy = apply_not_applicable_overrides(current, policy, Path(root))

            self.assertNotIn("required_status_checks", new_policy)
            self.assertTrue(new_policy["require_status_checks"])

    def test_does_not_mutate_the_original_dicts(self):
        with tempfile.TemporaryDirectory() as root:
            current = {"dependabot": False}
            policy = {"dependabot": True}

            apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(current, {"dependabot": False})
            self.assertEqual(policy, {"dependabot": True})


if __name__ == "__main__":
    unittest.main()
