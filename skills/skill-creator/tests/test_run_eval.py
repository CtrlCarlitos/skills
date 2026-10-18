"""Regression tests for scripts/run_eval.py's result aggregation.

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.run_eval import aggregate_results, find_conflicting_installed_skill, summarize


class SummarizeTests(unittest.TestCase):
    def test_errored_query_counts_as_errored_not_failed(self):
        results = [
            {"query": "a", "pass": True},
            {"query": "b", "pass": None},  # errored: no successful runs
        ]

        summary = summarize(results)

        self.assertEqual(summary, {"total": 2, "passed": 1, "failed": 0, "errored": 1})


class AggregateResultsTests(unittest.TestCase):
    def test_all_successful_runs_computes_trigger_rate_and_pass(self):
        eval_set = [{"query": "find the thing", "should_trigger": True}]
        query_outcomes = {"find the thing": [True, True, False]}

        out = aggregate_results(eval_set, query_outcomes, trigger_threshold=0.5)

        result = out["results"][0]
        self.assertAlmostEqual(result["trigger_rate"], 2 / 3)
        self.assertTrue(result["pass"])
        self.assertEqual(out["summary"], {"total": 1, "passed": 1, "failed": 0, "errored": 0})

    def test_harness_error_does_not_count_as_non_trigger(self):
        eval_set = [{"query": "find the thing", "should_trigger": True}]
        query_outcomes = {
            "find the thing": [RuntimeError("claude CLI not found")] * 3,
        }

        out = aggregate_results(eval_set, query_outcomes, trigger_threshold=0.5)

        result = out["results"][0]
        self.assertIsNone(result["pass"])
        self.assertEqual(result["errors"], 3)
        self.assertEqual(out["summary"], {"total": 1, "passed": 0, "failed": 0, "errored": 1})

    def test_partial_errors_compute_rate_from_successful_runs_only(self):
        eval_set = [{"query": "find the thing", "should_trigger": True}]
        query_outcomes = {
            "find the thing": [True, RuntimeError("timeout"), True],
        }

        out = aggregate_results(eval_set, query_outcomes, trigger_threshold=0.5)

        result = out["results"][0]
        self.assertEqual(result["trigger_rate"], 1.0)
        self.assertTrue(result["pass"])
        self.assertEqual(result["errors"], 1)
        self.assertEqual(out["summary"]["errored"], 0)


class FindConflictingInstalledSkillTests(unittest.TestCase):
    def test_no_conflict_when_nothing_installed(self):
        with tempfile.TemporaryDirectory() as project_root, tempfile.TemporaryDirectory() as fake_home:
            with mock.patch("scripts.run_eval.Path.home", return_value=Path(fake_home)):
                self.assertIsNone(find_conflicting_installed_skill(Path(project_root), "my-skill"))

    def test_detects_project_scoped_install(self):
        with tempfile.TemporaryDirectory() as project_root, tempfile.TemporaryDirectory() as fake_home:
            skill_dir = Path(project_root) / ".claude" / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n", encoding="utf-8")

            with mock.patch("scripts.run_eval.Path.home", return_value=Path(fake_home)):
                found = find_conflicting_installed_skill(Path(project_root), "my-skill")

            self.assertEqual(found, skill_dir / "SKILL.md")

    def test_detects_user_scoped_install(self):
        with tempfile.TemporaryDirectory() as project_root, tempfile.TemporaryDirectory() as fake_home:
            skill_dir = Path(fake_home) / ".claude" / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n", encoding="utf-8")

            with mock.patch("scripts.run_eval.Path.home", return_value=Path(fake_home)):
                found = find_conflicting_installed_skill(Path(project_root), "my-skill")

            self.assertEqual(found, skill_dir / "SKILL.md")

    def test_unrelated_skill_name_is_not_a_conflict(self):
        with tempfile.TemporaryDirectory() as project_root, tempfile.TemporaryDirectory() as fake_home:
            skill_dir = Path(project_root) / ".claude" / "skills" / "other-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: other-skill\n---\n", encoding="utf-8")

            with mock.patch("scripts.run_eval.Path.home", return_value=Path(fake_home)):
                self.assertIsNone(find_conflicting_installed_skill(Path(project_root), "my-skill"))


if __name__ == "__main__":
    unittest.main()
