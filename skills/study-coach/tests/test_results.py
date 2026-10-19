import json
import tempfile
import unittest
from pathlib import Path
from scripts.results import apply_review_grades, needs_review, parse_results_export

class ParseResultsExportTests(unittest.TestCase):
    def test_parses_a_well_formed_results_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "results.json"
            path.write_text(json.dumps([{"question_id": "q1", "given_answer": True, "correct": True}]), encoding="utf-8")

            results = parse_results_export(path)

            self.assertEqual(results, [{"question_id": "q1", "given_answer": True, "correct": True}])

    def test_rejects_a_file_that_is_not_a_list_of_question_records(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "results.json"
            path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                parse_results_export(path)

class NeedsReviewTests(unittest.TestCase):
    def test_lists_only_the_ungraded_open_response_questions(self):
        results = [
            {"question_id": "q1", "given_answer": True, "correct": True},
            {"question_id": "q2", "given_answer": "a paragraph", "correct": None},
        ]

        self.assertEqual(needs_review(results), ["q2"])

class ApplyReviewGradesTests(unittest.TestCase):
    def test_merges_a_grade_into_the_matching_question_without_touching_others(self):
        results = [
            {"question_id": "q1", "given_answer": True, "correct": True},
            {"question_id": "q2", "given_answer": "a paragraph", "correct": None},
        ]

        updated = apply_review_grades(results, {"q2": False})

        self.assertTrue(updated[0]["correct"])
        self.assertFalse(updated[1]["correct"])

    def test_ignores_a_grade_for_a_question_id_not_present_in_results(self):
        results = [{"question_id": "q1", "given_answer": True, "correct": True}]

        updated = apply_review_grades(results, {"ghost": False})

        self.assertEqual(updated, results)
