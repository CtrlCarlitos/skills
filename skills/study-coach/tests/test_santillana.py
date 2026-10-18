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

            source = record_santillana_photo(workspace, "lenguaje", "sustantivos", "4", photo)

            self.assertEqual(source["origin"], "santillana")
            self.assertEqual(source["subject"], "lenguaje")
            self.assertEqual(source["topic"], "sustantivos")
            self.assertEqual(source["grade"], "4")
            self.assertTrue(Path(source["cached_path"]).read_bytes() == b"fake-jpeg-bytes")
            found = find_cached_santillana_sources(workspace, "lenguaje", "sustantivos", "4")
            self.assertEqual(len(found), 1)

    def test_a_second_photo_for_the_same_subject_and_topic_accumulates_rather_than_replacing(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo1 = Path(root) / "page1.jpg"
            photo1.write_bytes(b"first-photo")
            photo2 = Path(root) / "page2.jpg"
            photo2.write_bytes(b"second-photo")

            record_santillana_photo(workspace, "lenguaje", "sustantivos", "4", photo1)
            record_santillana_photo(workspace, "lenguaje", "sustantivos", "4", photo2)

            found = find_cached_santillana_sources(workspace, "lenguaje", "sustantivos", "4")
            cached_bytes = {Path(s["cached_path"]).read_bytes() for s in found}
            self.assertEqual(len(found), 2)
            self.assertEqual(cached_bytes, {b"first-photo", b"second-photo"})

    def test_recording_after_an_earlier_photo_was_deleted_does_not_clobber_a_remaining_photo(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo_a = Path(root) / "a.jpg"
            photo_a.write_bytes(b"photo-a")
            photo_b = Path(root) / "b.jpg"
            photo_b.write_bytes(b"photo-b")
            photo_c = Path(root) / "c.jpg"
            photo_c.write_bytes(b"photo-c")

            first = record_santillana_photo(workspace, "lenguaje", "sustantivos", "4", photo_a)
            record_santillana_photo(workspace, "lenguaje", "sustantivos", "4", photo_b)
            Path(first["cached_path"]).unlink()
            record_santillana_photo(workspace, "lenguaje", "sustantivos", "4", photo_c)

            found_bytes = {
                Path(s["cached_path"]).read_bytes()
                for s in find_cached_santillana_sources(workspace, "lenguaje", "sustantivos", "4")
            }
            self.assertEqual(found_bytes, {b"photo-b", b"photo-c"})

    def test_a_stray_non_photo_file_in_the_topic_directory_is_never_counted_as_a_source(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")
            record_santillana_photo(workspace, "lenguaje", "verbos", "4", photo)

            junk_dir = workspace / "sources" / "santillana" / "lenguaje" / "4" / "verbos"
            (junk_dir / ".DS_Store").write_bytes(b"junk")

            found = find_cached_santillana_sources(workspace, "lenguaje", "verbos", "4")
            self.assertEqual(len(found), 1)

class FindCachedSantillanaSourcesTests(unittest.TestCase):
    def test_returns_empty_list_when_nothing_is_cached_for_that_topic(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            self.assertEqual(find_cached_santillana_sources(workspace, "matematica", "fracciones", "3"), [])
