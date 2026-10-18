import unittest

from scripts.editorconfig import build_editorconfig_gaps, parse_editorconfig


class ParseEditorconfigTests(unittest.TestCase):
    def test_parses_sections_into_pattern_and_settings(self):
        content = (
            "root = true\n\n"
            "[*.py]\nindent_style = space\nindent_size = 4\n\n"
            "[*.md]\ntrim_trailing_whitespace = false\n"
        )

        sections = parse_editorconfig(content)

        self.assertEqual(sections, [
            {"pattern": "*.py", "settings": {"indent_style": "space", "indent_size": "4"}},
            {"pattern": "*.md", "settings": {"trim_trailing_whitespace": "false"}},
        ])


class BuildEditorconfigGapsTests(unittest.TestCase):
    def test_reports_one_row_per_uncovered_extension_not_per_file(self):
        files = [
            {"path": "a.py", "mode": "100644", "has_shebang": False, "is_binary": False},
            {"path": "b.py", "mode": "100644", "has_shebang": False, "is_binary": False},
            {"path": "c.go", "mode": "100644", "has_shebang": False, "is_binary": False},
        ]

        gaps = build_editorconfig_gaps(files, existing_sections=[])

        extensions = {g["extension"] for g in gaps}
        self.assertEqual(extensions, {".py", ".go"})
        self.assertEqual(len(gaps), 2)

    def test_skips_extension_already_covered_by_a_section(self):
        files = [{"path": "a.py", "mode": "100644", "has_shebang": False, "is_binary": False}]
        existing_sections = [{"pattern": "*.py", "settings": {"indent_style": "space"}}]

        self.assertEqual(build_editorconfig_gaps(files, existing_sections), [])

    def test_skips_extensions_covered_by_a_brace_alternation_section(self):
        files = [
            {"path": "a.py", "mode": "100644", "has_shebang": False, "is_binary": False},
            {"path": "b.js", "mode": "100644", "has_shebang": False, "is_binary": False},
        ]
        existing_sections = [{"pattern": "*.{py,js}", "settings": {"indent_style": "space"}}]

        self.assertEqual(build_editorconfig_gaps(files, existing_sections), [])


if __name__ == "__main__":
    unittest.main()
