import tempfile
import unittest
from pathlib import Path
from scripts.santillana import find_cached_santillana_sources, record_santillana_photo
from scripts.workspace import resolve_workspace

class RecordSantillanaPhotoTests(unittest.TestCase):
    def test_records_a_photo_and_it_is_findable_afterward(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page1.jpg"
            photo.write_bytes(b"fake-jpeg-bytes")

            source = record_santillana_photo(workspace, "lenguaje", "sustantivos", photo)

            self.assertEqual(source["origin"], "santillana")
            self.assertEqual(source["subject"], "lenguaje")
            self.assertEqual(source["topic"], "sustantivos")
            self.assertTrue(Path(source["cached_path"]).read_bytes() == b"fake-jpeg-bytes")
            found = find_cached_santillana_sources(workspace, "lenguaje", "sustantivos")
            self.assertEqual(len(found), 1)

    def test_a_second_photo_for_the_same_subject_and_topic_accumulates_rather_than_replacing(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo1 = Path(root) / "page1.jpg"
            photo1.write_bytes(b"first-photo")
            photo2 = Path(root) / "page2.jpg"
            photo2.write_bytes(b"second-photo")

            record_santillana_photo(workspace, "lenguaje", "sustantivos", photo1)
            record_santillana_photo(workspace, "lenguaje", "sustantivos", photo2)

            found = find_cached_santillana_sources(workspace, "lenguaje", "sustantivos")
            cached_bytes = {Path(s["cached_path"]).read_bytes() for s in found}
            self.assertEqual(len(found), 2)
            self.assertEqual(cached_bytes, {b"first-photo", b"second-photo"})

class FindCachedSantillanaSourcesTests(unittest.TestCase):
    def test_returns_empty_list_when_nothing_is_cached_for_that_topic(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            self.assertEqual(find_cached_santillana_sources(workspace, "matematica", "fracciones"), [])
