import json
import tempfile
import unittest
from pathlib import Path
from scripts.dashboard import record_exam_report, render_dashboard_html
from scripts.workspace import child_dir, resolve_workspace

class RecordExamReportTests(unittest.TestCase):
    def test_creates_the_history_file_on_the_first_exam(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")

            history_path = record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [
                {"subject": "lenguaje", "topic": "sustantivos", "correct": 3, "total": 4, "strength": "solid"},
            ])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["exam_id"], "exam1")

    def test_a_second_exam_for_the_same_subject_accumulates_rather_than_replacing(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [])

            history_path = record_exam_report(mateo, "exam2", "lenguaje", "adjetivos", "2026-10-25", [])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual([h["exam_id"] for h in history], ["exam1", "exam2"])

    def test_recording_the_same_exam_id_again_replaces_its_entry_rather_than_duplicating_it(self):
        # This is what lets a parent's open-response review (which re-runs
        # scoring for the same exam after merging a review grade) update
        # the existing entry instead of appending a second, stale one.
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [
                {"subject": "lenguaje", "topic": "sustantivos", "correct": 1, "total": 2, "strength": "needs_work"},
            ])

            history_path = record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [
                {"subject": "lenguaje", "topic": "sustantivos", "correct": 2, "total": 2, "strength": "solid"},
            ])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["topic_reports"][0]["strength"], "solid")

class RenderDashboardHtmlTests(unittest.TestCase):
    def test_renders_every_childs_exam_history_and_writes_index_html(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [
                {"subject": "lenguaje", "topic": "sustantivos", "correct": 3, "total": 4, "strength": "solid"},
            ])

            html = render_dashboard_html(workspace)

            self.assertIn("mateo", html)
            self.assertIn("sustantivos", html)
            self.assertEqual((workspace / "index.html").read_text(encoding="utf-8"), html)

    def test_a_child_with_no_exams_yet_does_not_crash_the_dashboard(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            child_dir(workspace, "mateo")

            html = render_dashboard_html(workspace)

            self.assertIn("mateo", html)
