import unittest

from scripts.report import render_markdown


class RenderMarkdownTests(unittest.TestCase):
    def test_renders_only_nonempty_sections(self):
        output = render_markdown(
            gitattributes_gaps=[{"path": "deploy.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "patch file"}],
            exec_bit_gaps=[],
            editorconfig_gaps=[],
            gitignore_gaps=[],
        )

        self.assertIn("## .gitattributes gaps", output)
        self.assertIn("deploy.patch", output)
        self.assertNotIn("## Executable-bit drift", output)

    def test_all_empty_reports_no_gaps(self):
        self.assertEqual(render_markdown([], [], [], []), "No gaps found.")


if __name__ == "__main__":
    unittest.main()
