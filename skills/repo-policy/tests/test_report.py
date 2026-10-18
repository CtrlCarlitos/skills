"""Tests for the Markdown matrix renderer.

Run from skills/repo-policy/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.report import render_markdown


class RenderMarkdownTests(unittest.TestCase):
    def test_renders_the_header_and_separator_row(self):
        markdown = render_markdown([])

        lines = markdown.splitlines()
        self.assertEqual(lines[0], "| Setting / policy | Current | Target | Action |")
        self.assertEqual(lines[1], "|---|---|---|---|")

    def test_renders_one_row_per_setting(self):
        rows = [
            {"label": "Default branch", "current": "main", "target": "main", "action": "None", "exception_reason": None},
            {"label": "PR required", "current": "False", "target": "True", "action": "Add rule", "exception_reason": None},
        ]

        markdown = render_markdown(rows)

        self.assertIn("| Default branch | main | main | None |", markdown)
        self.assertIn("| PR required | False | True | Add rule |", markdown)

    def test_exception_row_shows_its_reason_instead_of_the_bare_action(self):
        rows = [{
            "label": "Signed commits",
            "current": "False",
            "target": "True",
            "action": "Exception",
            "exception_reason": "contributors sign via SSH keys GitHub can't verify yet",
        }]

        markdown = render_markdown(rows)

        self.assertIn("Exception: contributors sign via SSH keys GitHub can't verify yet", markdown)

    def test_pipe_characters_in_values_are_escaped_so_the_table_does_not_break(self):
        rows = [{"label": "A|B", "current": "x|y", "target": "z", "action": "None", "exception_reason": None}]

        markdown = render_markdown(rows)

        self.assertIn(r"A\|B", markdown)
        self.assertIn(r"x\|y", markdown)


if __name__ == "__main__":
    unittest.main()
