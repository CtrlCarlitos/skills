"""Tests for the pure current-vs-policy comparison engine.

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.compare import Setting, build_matrix


class BuildMatrixTests(unittest.TestCase):
    def test_matching_setting_has_no_action(self):
        settings = [Setting(key="default_branch", label="Default branch", action_when_mismatched="Rename")]
        current = {"default_branch": "main"}
        target = {"default_branch": "main"}

        rows = build_matrix(current, target, settings)

        self.assertEqual(rows, [{
            "label": "Default branch",
            "current": "main",
            "target": "main",
            "action": "None",
            "exception_reason": None,
        }])

    def test_mismatched_setting_uses_the_settings_action_verb(self):
        settings = [Setting(key="require_pull_request", label="PR required", action_when_mismatched="Add rule")]
        current = {"require_pull_request": False}
        target = {"require_pull_request": True}

        rows = build_matrix(current, target, settings)

        self.assertEqual(rows[0]["action"], "Add rule")

    def test_documented_exception_overrides_the_action_verb(self):
        """Issue #5: "Repository-specific CI checks and justified exceptions must
        remain configurable" -- a documented exception must not be reported as a
        plain gap to fix."""
        settings = [Setting(key="required_signatures", label="Signed commits", action_when_mismatched="Enable")]
        current = {"required_signatures": False}
        target = {"required_signatures": True}
        exceptions = {"required_signatures": "contributors sign via SSH keys GitHub can't verify yet"}

        rows = build_matrix(current, target, settings, exceptions=exceptions)

        self.assertEqual(rows[0]["action"], "Exception")
        self.assertEqual(rows[0]["exception_reason"], exceptions["required_signatures"])

    def test_custom_format_function_renders_the_display_value(self):
        settings = [Setting(
            key="required_status_checks",
            label="Required CI",
            action_when_mismatched="Update checks",
            format=lambda v: ", ".join(v) if v else "(none)",
        )]
        current = {"required_status_checks": []}
        target = {"required_status_checks": ["build", "test"]}

        rows = build_matrix(current, target, settings)

        self.assertEqual(rows[0]["current"], "(none)")
        self.assertEqual(rows[0]["target"], "build, test")

    def test_missing_current_value_is_treated_as_none(self):
        """A setting the inspector didn't find anything for (e.g. a file that
        doesn't exist) is a real gap, not an error."""
        settings = [Setting(key="codeowners", label="CODEOWNERS", action_when_mismatched="Create")]
        current = {}
        target = {"codeowners": "present"}

        rows = build_matrix(current, target, settings)

        self.assertEqual(rows[0]["current"], "None")
        self.assertEqual(rows[0]["action"], "Create")


if __name__ == "__main__":
    unittest.main()
