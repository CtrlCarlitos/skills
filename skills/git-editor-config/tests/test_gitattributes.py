import unittest

from scripts.gitattributes import is_covered, parse_gitattributes, pattern_matches, resolve_attributes


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

    def test_a_leading_doublestar_slash_matches_at_the_root_too(self):
        # fnmatch alone treats "/" in the pattern as a literal character, so
        # "**/*.sh" (a common real-world idiom meaning "at any depth,
        # including the root") would otherwise never match a root-level
        # "run.sh", which has no "/" in it at all.
        self.assertTrue(pattern_matches("**/*.sh", "run.sh"))
        self.assertTrue(pattern_matches("**/*.sh", "scripts/run.sh"))

    def test_a_brace_alternation_matches_any_of_its_options(self):
        self.assertTrue(pattern_matches("*.{py,js}", "a.py"))
        self.assertTrue(pattern_matches("*.{py,js}", "a.js"))
        self.assertFalse(pattern_matches("*.{py,js}", "a.go"))


class IsCoveredTests(unittest.TestCase):
    def test_is_covered_true_only_when_a_rule_matches(self):
        rules = [{"pattern": "*.sh", "attrs": ["text", "eol=lf"]}]

        self.assertTrue(is_covered("scripts/run.sh", rules))
        self.assertFalse(is_covered("notes.txt", rules))


class ResolveAttributesTests(unittest.TestCase):
    def test_later_rule_overrides_an_earlier_one_per_attribute_name(self):
        rules = [
            {"pattern": "*", "attrs": ["text=auto", "eol=lf"]},
            {"pattern": "*.patch", "attrs": ["-diff"]},
        ]

        self.assertEqual(resolve_attributes("deploy.patch", rules), {"text": "auto", "eol": "lf", "diff": False})

    def test_non_matching_rules_contribute_nothing(self):
        rules = [{"pattern": "*.sh", "attrs": ["-text"]}]

        self.assertEqual(resolve_attributes("notes.txt", rules), {})

    def test_a_bare_attribute_name_resolves_to_true(self):
        rules = [{"pattern": "*.sh", "attrs": ["text"]}]

        self.assertEqual(resolve_attributes("run.sh", rules), {"text": True})

    def test_a_negated_attribute_resolves_to_false(self):
        rules = [{"pattern": "*.png", "attrs": ["-text", "-diff"]}]

        self.assertEqual(resolve_attributes("logo.png", rules), {"text": False, "diff": False})


if __name__ == "__main__":
    unittest.main()
