import tempfile
import unittest
from pathlib import Path
from scripts.grounding import ground_topic
from scripts.workspace import resolve_workspace

class GroundTopicTests(unittest.TestCase):
    def test_non_curricular_topic_skips_mineducyt_and_santillana_entirely(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = ground_topic(workspace, "youtube", "channel-setup", grade="n/a", is_curricular=False)

            self.assertEqual(result, {"sources": [], "gap": None})

    def test_curricular_topic_with_a_mineducyt_match_uses_it(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = ground_topic(
                workspace, "matematica", "fracciones", grade="3", is_curricular=True,
                download=lambda url: b"%PDF-fake",
            )

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "mineducyt")
            self.assertIsNone(result["gap"])

    def test_curricular_topic_with_no_mineducyt_entry_and_no_photo_reports_a_gap(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True)

            self.assertEqual(result["sources"], [])
            self.assertIsNotNone(result["gap"])

    def test_curricular_topic_with_no_mineducyt_entry_but_a_supplied_photo_uses_the_photo(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")

            result = ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True, santillana_photo_path=photo)

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "santillana")
            self.assertIsNone(result["gap"])

    def test_curricular_topic_reuses_an_already_cached_photo_without_a_new_supply(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")
            ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True, santillana_photo_path=photo)

            result = ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True)

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "santillana")
            self.assertIsNone(result["gap"])

    def test_a_santillana_photo_recorded_for_one_grade_does_not_ground_a_different_grade(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")
            ground_topic(workspace, "lenguaje", "adjetivos", grade="3", is_curricular=True, santillana_photo_path=photo)

            result = ground_topic(workspace, "lenguaje", "adjetivos", grade="5", is_curricular=True)

            self.assertEqual(result["sources"], [])
            self.assertIsNotNone(result["gap"])

    def test_a_failed_mineducyt_download_still_allows_the_santillana_fallback_to_be_used(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")

            def failing_download(url):
                raise OSError("network down")

            result = ground_topic(
                workspace, "matematica", "fracciones", grade="3", is_curricular=True,
                santillana_photo_path=photo, download=failing_download,
            )

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "santillana")
            self.assertIsNone(result["gap"])
