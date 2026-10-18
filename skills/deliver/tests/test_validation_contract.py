"""Tests for the local-validation-contract builder: parse a GitHub Actions
workflow into its actual steps, map each runnable step to the exact local
command (no separate local/remote check logic -- the issue's own
requirement), flag non-runnable steps (actions like `actions/checkout`)
as CI-only with a reason, and classify `continue-on-error` steps as
optional rather than required.

Uses this repo's own real .github/workflows/ci.yml as a fixture for the
parse step -- not a hand-written stand-in -- since that's the actual
artifact this tool has to handle correctly.

Run from skills/deliver/: python3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

from scripts.validation_contract import build_local_validation_contract, parse_ci_steps, run_contract

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REAL_CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

SYNTHETIC_WORKFLOW = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: run tests
        working-directory: skills/example
        run: python3 -m unittest discover -s tests -v
      - name: known-flaky check
        continue-on-error: true
        run: bash scripts/flaky-check.sh
"""


class ParseCiStepsTests(unittest.TestCase):
    def test_parses_this_repos_own_real_workflow(self):
        steps = parse_ci_steps(REAL_CI_WORKFLOW.read_text(encoding="utf-8"))

        job_names = {s["job"] for s in steps}
        self.assertIn("vendor-check", job_names)

        release_notes_step = next(
            s for s in steps if s["step_name"] == "release-notes regression tests" and s["job"] == "vendor-check"
        )
        self.assertEqual(release_notes_step["working_directory"], "skills/release-notes")
        self.assertIn("python3 -m unittest discover -s tests -v", release_notes_step["run"])

    def test_parses_a_synthetic_workflow_shape(self):
        steps = parse_ci_steps(SYNTHETIC_WORKFLOW)

        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0]["uses"], "actions/checkout@v4")
        self.assertIsNone(steps[0]["run"])
        self.assertEqual(steps[1]["step_name"], "run tests")
        self.assertEqual(steps[1]["working_directory"], "skills/example")
        self.assertFalse(steps[2].get("continue_on_error") is None)
        self.assertTrue(steps[2]["continue_on_error"])


class BuildLocalValidationContractTests(unittest.TestCase):
    def test_splits_runnable_steps_from_ci_only_action_steps(self):
        steps = parse_ci_steps(SYNTHETIC_WORKFLOW)

        contract, ci_only = build_local_validation_contract(steps)

        self.assertEqual(len(ci_only), 1)
        self.assertEqual(ci_only[0]["uses"], "actions/checkout@v4")
        self.assertIn("reason", ci_only[0])
        self.assertEqual(len(contract), 2)

    def test_classifies_continue_on_error_steps_as_optional(self):
        steps = parse_ci_steps(SYNTHETIC_WORKFLOW)

        contract, _ = build_local_validation_contract(steps)

        statuses = {c["step_name"]: c["status"] for c in contract}
        self.assertEqual(statuses["run tests"], "required")
        self.assertEqual(statuses["known-flaky check"], "optional")


class RunContractTests(unittest.TestCase):
    def test_runs_each_entry_and_reports_pass_fail(self):
        contract = [
            {"job": "build", "step_name": "a passing check", "command": "true", "working_directory": None, "status": "required"},
            {"job": "build", "step_name": "a failing check", "command": "false", "working_directory": None, "status": "required"},
        ]

        results = run_contract(contract, REPO_ROOT)

        passed = {r["step_name"]: r["passed"] for r in results}
        self.assertTrue(passed["a passing check"])
        self.assertFalse(passed["a failing check"])

    def test_respects_the_steps_working_directory(self):
        contract = [
            {
                "job": "build",
                "step_name": "pwd check",
                "command": "test \"$(basename \"$PWD\")\" = skills",
                "working_directory": "skills",
                "status": "required",
            }
        ]

        results = run_contract(contract, REPO_ROOT)

        self.assertTrue(results[0]["passed"])

    def test_a_real_failing_command_reports_its_output(self):
        contract = [
            {"job": "build", "step_name": "echo then fail", "command": "echo something-specific; exit 1", "working_directory": None, "status": "required"}
        ]

        results = run_contract(contract, REPO_ROOT)

        self.assertFalse(results[0]["passed"])
        self.assertIn("something-specific", results[0]["output"])


if __name__ == "__main__":
    unittest.main()
