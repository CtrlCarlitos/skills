import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

_EXAM = {
    "exam_id": "exam1", "child_id": "mateo", "subject": "lenguaje", "topic": "sustantivos", "grade": "4",
    "questions": [
        {
            "question_id": "q1", "type": "true_false", "subject": "lenguaje", "topic": "sustantivos",
            "competency": None, "prompt": "Perro is a noun.", "options": None, "correct_answer": True,
        },
        {
            "question_id": "q2", "type": "true_false", "subject": "lenguaje", "topic": "sustantivos",
            "competency": None, "prompt": "Correr is a noun.", "options": None, "correct_answer": False,
        },
    ],
}

class AuditExamCliTests(unittest.TestCase):
    def test_render_writes_a_self_contained_html_file(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            out_path = Path(root) / "exam.html"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_exam", "render", str(exam_path), str(out_path)],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("Perro is a noun.", out_path.read_text(encoding="utf-8"))

    def test_score_reports_a_gap_and_updates_the_dashboard(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            results_path = Path(root) / "results.json"
            results_path.write_text(json.dumps([
                {"question_id": "q1", "given_answer": False, "correct": False},
                {"question_id": "q2", "given_answer": True, "correct": False},
            ]), encoding="utf-8")
            workspace = Path(root) / "family"

            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_exam", "score", str(exam_path), str(results_path), str(workspace), "mateo", "2026-10-18"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("needs_work", result.stdout)
            self.assertTrue((workspace / "children" / "mateo" / "subjects" / "lenguaje" / "exam_history.json").exists())
            self.assertTrue((workspace / "index.html").exists())

    def test_score_recomputes_correctness_from_grading_py_ignoring_the_pages_own_correct_field(self):
        # The exported "correct" field comes from a second, independent
        # implementation of grading logic running in the browser. The CLI
        # must recompute from given_answer via grading.score_exam, not
        # trust whatever the page claims -- this test's results file
        # deliberately lies ("correct": false for two right answers) to
        # prove the lie is ignored.
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            results_path = Path(root) / "results.json"
            results_path.write_text(json.dumps([
                {"question_id": "q1", "given_answer": True, "correct": False},
                {"question_id": "q2", "given_answer": False, "correct": False},
            ]), encoding="utf-8")
            workspace = Path(root) / "family"

            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_exam", "score", str(exam_path), str(results_path), str(workspace), "mateo", "2026-10-18"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("solid", result.stdout)
            self.assertNotIn("needs_work", result.stdout)

    def test_score_with_grades_file_merges_review_grades_for_open_response_questions(self):
        exam = {
            "exam_id": "exam2", "child_id": "mateo", "subject": "lenguaje", "topic": "redaccion", "grade": "4",
            "questions": [
                {
                    "question_id": "q1", "type": "true_false", "subject": "lenguaje", "topic": "redaccion",
                    "competency": None, "prompt": "Perro is a noun.", "options": None, "correct_answer": True,
                },
                {
                    "question_id": "q2", "type": "open_response", "subject": "lenguaje", "topic": "redaccion",
                    "competency": None, "prompt": "Write a sentence.", "options": None, "correct_answer": None,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(exam), encoding="utf-8")
            results_path = Path(root) / "results.json"
            results_path.write_text(json.dumps([
                {"question_id": "q1", "given_answer": True, "correct": True},
                {"question_id": "q2", "given_answer": "Mi perro es grande.", "correct": None},
            ]), encoding="utf-8")
            grades_path = Path(root) / "grades.json"
            grades_path.write_text(json.dumps({"q2": True}), encoding="utf-8")
            workspace = Path(root) / "family"

            result = subprocess.run(
                [
                    sys.executable, "-m", "scripts.audit_exam", "score",
                    str(exam_path), str(results_path), str(workspace), "mateo", "2026-10-18",
                    "--grades", str(grades_path),
                ],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertNotIn("needs review", result.stdout)
            self.assertIn("solid", result.stdout)
