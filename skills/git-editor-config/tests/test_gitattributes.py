import unittest

from scripts.gitattributes import is_covered, parse_gitattributes, pattern_matches


class ParseGitattributesTests(unittest.TestCase):
    def test_parses_rules_skipping_comments_and_blanks(self):
        content = "# comment\n*.sh text eol=lf\n\n*.patch text eol=lf -diff\n"

        rules = parse_gitattributes(content)

        self.assertEqual(rules, [
            {"pattern": "*.sh", "attrs": ["text", "eol=lf"]},
            {"pattern": "*.patch", "attrs": ["text", "eol=lf", "-diff"]},
        ])


class PatternMatchesTests(unittest.TestCase):
    def test_pattern_matches_a_bare_extension_glob(self):
        self.assertTrue(pattern_matches("*.sh", "scripts/run.sh"))
        self.assertFalse(pattern_matches("*.sh", "run.py"))


class IsCoveredTests(unittest.TestCase):
    def test_is_covered_true_only_when_a_rule_matches(self):
        rules = [{"pattern": "*.sh", "attrs": ["text", "eol=lf"]}]

        self.assertTrue(is_covered("scripts/run.sh", rules))
        self.assertFalse(is_covered("notes.txt", rules))


if __name__ == "__main__":
    unittest.main()
