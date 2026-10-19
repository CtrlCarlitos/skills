import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

_EXAM = {
    "exam_id": "exam1", "child_id": "mateo", "subject": "lenguaje", "topic": "sustantivos", "grade": "4",
    "questions": [{
        "question_id": "q1", "type": "true_false", "subject": "lenguaje", "topic": "sustantivos",
        "competency": None, "prompt": "Perro is a noun.", "options": None, "correct_answer": True,
    }],
}
_DECK = {
    "deck_id": "deck1", "child_id": "mateo", "subject": "lenguaje", "topic": "sustantivos",
    "cards": [{"card_id": "c1", "subject": "lenguaje", "topic": "sustantivos", "competency": None, "prompt": "Perro", "answer": "Sustantivo"}],
}

class AuditBundleBuildCliTests(unittest.TestCase):
    def test_writes_the_exam_and_flashcard_pages_and_the_topic_index(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            deck_path = Path(root) / "deck.json"
            deck_path.write_text(json.dumps(_DECK), encoding="utf-8")
            workspace = Path(root) / "family"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_bundle", "build", str(workspace), "mateo", str(exam_path), str(deck_path)],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            topic = workspace / "children" / "mateo" / "subjects" / "lenguaje" / "sustantivos"
            self.assertIn("Perro is a noun.", (topic / "exam.html").read_text(encoding="utf-8"))
            self.assertIn("Perro", (topic / "flashcards.html").read_text(encoding="utf-8"))
            self.assertFalse((topic / "practice.html").exists())
            self.assertIn("exam.html", (topic / "index.html").read_text(encoding="utf-8"))

    def test_practice_flag_also_writes_a_practice_page(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            deck_path = Path(root) / "deck.json"
            deck_path.write_text(json.dumps(_DECK), encoding="utf-8")
            workspace = Path(root) / "family"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_bundle", "build", str(workspace), "mateo", str(exam_path), str(deck_path), "--practice"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            topic = workspace / "children" / "mateo" / "subjects" / "lenguaje" / "sustantivos"
            self.assertTrue((topic / "practice.html").exists())
            self.assertNotIn("downloadResults", (topic / "practice.html").read_text(encoding="utf-8"))

class AuditBundleRecordCliTests(unittest.TestCase):
    def test_records_a_flashcard_session_from_the_downloaded_results_export(self):
        with tempfile.TemporaryDirectory() as root:
            deck_path = Path(root) / "deck.json"
            deck_path.write_text(json.dumps(_DECK), encoding="utf-8")
            results_path = Path(root) / "results.json"
            results_path.write_text(json.dumps({"deck_id": "deck1", "results": [{"card_id": "c1", "result": "incorrect"}]}), encoding="utf-8")
            workspace = Path(root) / "family"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_bundle", "record", str(workspace), "mateo", str(deck_path), str(results_path), "2026-10-19"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            history_path = workspace / "children" / "mateo" / "subjects" / "lenguaje" / "flashcard_history.json"
            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(history[0]["deck_id"], "deck1")
            self.assertEqual(history[0]["results"], [{"card_id": "c1", "result": "incorrect"}])
