import tempfile
import unittest
from pathlib import Path

from scripts import check_frontmatter


VALID = "---\nname: example\ndescription: Does something useful.\n---\nbody\n"
# The exact shape that shipped broken on 2026-11-13: an unquoted description
# whose plain scalar contains `entry points: "full bundle"` (a colon-space is
# a mapping indicator in YAML). The skills CLI skipped the whole skill for
# this and still exited 0.
UNQUOTED_COLON = (
    "---\nname: example\ndescription: Two parent-facing entry points: "
    '"full bundle" and "quick answer".\n---\nbody\n'
)
QUOTED_COLON = (
    '---\nname: example\ndescription: "Two axes: Standards and Spec, '
    'with a quoted \\"review since X\\" phrase."\n---\nbody\n'
)


class FrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.skills = Path(self.temp_dir.name) / "skills"

    def write(self, text, folder="example"):
        path = self.skills / folder / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_frontmatter_passes(self):
        self.write(VALID)
        check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_quoted_description_with_colon_passes(self):
        self.write(QUOTED_COLON)
        check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_unquoted_colon_in_description_fails(self):
        self.write(UNQUOTED_COLON)
        with self.assertRaises(check_frontmatter.FrontmatterError):
            check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_missing_description_fails(self):
        self.write("---\nname: example\n---\nbody\n")
        with self.assertRaises(check_frontmatter.FrontmatterError):
            check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_empty_name_fails(self):
        self.write("---\nname: ''\ndescription: Does something.\n---\nbody\n")
        with self.assertRaises(check_frontmatter.FrontmatterError):
            check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_name_not_matching_folder_fails(self):
        self.write(VALID.replace("name: example", "name: other"), folder="example")
        with self.assertRaises(check_frontmatter.FrontmatterError):
            check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_missing_frontmatter_block_fails(self):
        self.write("name: example\ndescription: no fences.\n")
        with self.assertRaises(check_frontmatter.FrontmatterError):
            check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_non_mapping_frontmatter_fails(self):
        self.write("---\n- a\n- b\n---\nbody\n")
        with self.assertRaises(check_frontmatter.FrontmatterError):
            check_frontmatter.check_skill_md(self.skills / "example" / "SKILL.md")

    def test_main_passes_a_valid_tree(self):
        self.write(VALID)
        self.assertEqual(check_frontmatter.main([str(self.skills)]), 0)

    def test_main_fails_a_broken_tree(self):
        self.write(UNQUOTED_COLON)
        self.assertEqual(check_frontmatter.main([str(self.skills)]), 1)

    def test_main_fails_an_empty_tree(self):
        self.assertEqual(check_frontmatter.main([str(self.skills)]), 1)


if __name__ == "__main__":
    unittest.main()
