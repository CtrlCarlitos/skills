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

    def test_a_protection_the_policy_does_not_require_is_never_proposed_for_removal(self):
        """A policy's `false` on an on/off setting means "not required", not
        "turn it off": CtrlCarlitos/dotfiles signs commits and the default
        policy's `required_signatures: false` showed "Enable" -- applying it
        would have removed the protection."""
        settings = [Setting(key="required_signatures", label="Signed commits", action_when_mismatched="Enable")]

        rows = build_matrix({"required_signatures": True}, {"required_signatures": False}, settings)

        self.assertEqual(rows[0]["action"], "None (exceeds policy)")

    def test_a_required_protection_that_is_missing_is_still_a_gap(self):
        settings = [Setting(key="required_signatures", label="Signed commits", action_when_mismatched="Enable")]

        rows = build_matrix({"required_signatures": False}, {"required_signatures": True}, settings)

        self.assertEqual(rows[0]["action"], "Enable")

    def test_a_count_mismatch_says_which_way_to_move(self):
        """Lowering approvals is a real change worth proposing (the
        single-maintainer trap), so a count says raise or lower."""
        settings = [Setting(key="required_approving_review_count", label="Required approvals", action_when_mismatched="Set count")]

        lower = build_matrix({"required_approving_review_count": 1}, {"required_approving_review_count": 0}, settings)
        raise_ = build_matrix({"required_approving_review_count": 0}, {"required_approving_review_count": 2}, settings)

        self.assertEqual(lower[0]["action"], "Lower count")
        self.assertEqual(raise_[0]["action"], "Raise count")

    def test_a_setting_the_policy_omits_is_not_audited(self):
        """default-policy.yaml: "every key here is optional; omit what you
        don't want audited." An omitted key must not become a row whose
        target is None and whose action asks to change the repo (#42)."""
        settings = [
            Setting(key="default_branch", label="Default branch", action_when_mismatched="Rename"),
            Setting(key="allow_auto_merge", label="Auto-merge allowed", action_when_mismatched="Enable"),
        ]
        current = {"default_branch": "main", "allow_auto_merge": False}
        target = {"default_branch": "main"}

        rows = build_matrix(current, target, settings)

        self.assertEqual([r["label"] for r in rows], ["Default branch"])


if __name__ == "__main__":
    unittest.main()
