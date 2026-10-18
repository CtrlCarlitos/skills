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

    def test_agents_md_becomes_na_on_both_sides_when_repo_is_not_agentic(self):
        with tempfile.TemporaryDirectory() as root:
            current = {"agents_md": False}
            policy = {"agents_md": True}

            new_current, new_policy = apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(new_current["agents_md"], "N/A")
            self.assertEqual(new_policy["agents_md"], "N/A")

    def test_does_not_mutate_the_original_dicts(self):
        with tempfile.TemporaryDirectory() as root:
            current = {"dependabot": False}
            policy = {"dependabot": True}

            apply_not_applicable_overrides(current, policy, Path(root))

            self.assertEqual(current, {"dependabot": False})
            self.assertEqual(policy, {"dependabot": True})


if __name__ == "__main__":
    unittest.main()
