import tempfile
import unittest
from pathlib import Path
from scripts.mineducyt import fetch_mineducyt_source

class FetchMineducytSourceTests(unittest.TestCase):
    def test_returns_none_when_there_is_no_registry_entry(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            result = fetch_mineducyt_source("lenguaje", "4", Path(cache_dir), download=lambda url: b"unused")

            self.assertIsNone(result)

    def test_downloads_and_caches_a_registered_source(self):
        calls = []
        def fake_download(url):
            calls.append(url)
            return b"%PDF-fake-bytes"

        with tempfile.TemporaryDirectory() as cache_dir:
            result = fetch_mineducyt_source("matematica", "3", Path(cache_dir), download=fake_download)

            self.assertEqual(result["origin"], "mineducyt")
            self.assertEqual(result["subject"], "matematica")
            self.assertEqual(result["grade"], "3")
            self.assertEqual(len(calls), 1)
            self.assertTrue(Path(result["cached_path"]).read_bytes().startswith(b"%PDF"))

    def test_does_not_re_download_an_already_cached_source(self):
        calls = []
        def fake_download(url):
            calls.append(url)
            return b"%PDF-fake-bytes"

        with tempfile.TemporaryDirectory() as cache_dir:
            fetch_mineducyt_source("matematica", "3", Path(cache_dir), download=fake_download)
            fetch_mineducyt_source("matematica", "3", Path(cache_dir), download=fake_download)

            self.assertEqual(len(calls), 1)
