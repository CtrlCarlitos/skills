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

    def test_a_rewrite_that_omits_a_previously_written_file_removes_it(self):
        # A bundle is "current materials," not a log: regenerating with
        # only exam_html must not leave a stale flashcards.html/practice.html
        # around implying they're still current when they may no longer
        # match the regenerated content.
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            write_bundle_files(
                mateo, "lenguaje", "sustantivos",
                exam_html="<html>exam</html>", flashcard_html="<html>cards</html>", practice_html="<html>practice</html>",
            )

            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v2</html>")

            self.assertEqual(set(written), {"exam"})
            topic = topic_dir(mateo, "lenguaje", "sustantivos")
            self.assertFalse((topic / "flashcards.html").exists())
            self.assertFalse((topic / "practice.html").exists())

class RenderTopicIndexHtmlTests(unittest.TestCase):
    def test_links_only_the_files_actually_present_on_disk(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam</html>", flashcard_html="<html>cards</html>")

            html = render_topic_index_html(mateo, "lenguaje", "sustantivos")

            self.assertIn("exam.html", html)
            self.assertIn("flashcards.html", html)
            self.assertNotIn("practice.html", html)
            self.assertEqual((topic_dir(mateo, "lenguaje", "sustantivos") / "index.html").read_text(encoding="utf-8"), html)

    def test_reflects_disk_state_even_when_called_without_this_calls_written_dict(self):
        # render_topic_index_html must never trust a caller-supplied
        # "written" record of what happened in one call -- it has to be
        # built from what is actually on disk right now, or it can drift
        # from reality the moment a bundle is partially rewritten.
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam</html>", flashcard_html="<html>cards</html>")
            write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v2</html>")

            html = render_topic_index_html(mateo, "lenguaje", "sustantivos")

            self.assertIn("exam.html", html)
            self.assertNotIn("flashcards.html", html)
