import unittest
from scripts.sources import make_source, format_citation

class MakeSourceTests(unittest.TestCase):
    def test_builds_a_source_record_with_all_fields(self):
        source = make_source("mineducyt", "Libro de texto 3.° grado", "https://www.mined.gob.sv/.../3.pdf", cached_path="/cache/mat3.pdf", subject="matematica", topic="fracciones", grade="3")
        self.assertEqual(source, {
            "origin": "mineducyt", "title": "Libro de texto 3.° grado",
            "url_or_path": "https://www.mined.gob.sv/.../3.pdf", "cached_path": "/cache/mat3.pdf",
            "subject": "matematica", "topic": "fracciones", "grade": "3",
        })

class FormatCitationTests(unittest.TestCase):
    def test_renders_a_one_line_citation(self):
        source = make_source("mineducyt", "Libro de texto 3.° grado", "https://www.mined.gob.sv/x.pdf")
        citation = format_citation(source)
        self.assertIn("Libro de texto 3.° grado", citation)
        self.assertIn("https://www.mined.gob.sv/x.pdf", citation)
