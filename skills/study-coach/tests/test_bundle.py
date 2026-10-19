import tempfile
import unittest
from pathlib import Path
from scripts.bundle import render_topic_index_html, topic_dir, write_bundle_files
from scripts.workspace import child_dir, resolve_workspace

class WriteBundleFilesTests(unittest.TestCase):
    def test_writes_only_the_given_files(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")

            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v1</html>")

            self.assertEqual(set(written), {"exam"})
            self.assertEqual(written["exam"].read_text(encoding="utf-8"), "<html>exam v1</html>")

    def test_a_second_write_overwrites_the_first_rather_than_accumulating(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v1</html>")

            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v2</html>")

            self.assertEqual(written["exam"].read_text(encoding="utf-8"), "<html>exam v2</html>")
            self.assertEqual(len(list(topic_dir(mateo, "lenguaje", "sustantivos").iterdir())), 1)

class RenderTopicIndexHtmlTests(unittest.TestCase):
    def test_links_only_the_files_that_were_actually_written(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam</html>", flashcard_html="<html>cards</html>")

            html = render_topic_index_html(mateo, "lenguaje", "sustantivos", written)

            self.assertIn("exam.html", html)
            self.assertIn("flashcards.html", html)
            self.assertNotIn("practice.html", html)
            self.assertEqual((topic_dir(mateo, "lenguaje", "sustantivos") / "index.html").read_text(encoding="utf-8"), html)
