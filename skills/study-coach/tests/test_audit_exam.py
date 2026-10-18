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
