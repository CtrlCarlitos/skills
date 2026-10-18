import unittest

from scripts.gaps import build_exec_bit_gaps, build_gitattributes_gaps


class BuildGitattributesGapsTests(unittest.TestCase):
    def test_skips_already_covered_file(self):
        files = [{"path": "run.sh", "mode": "100755", "has_shebang": True, "is_binary": False}]
        existing_rules = [{"pattern": "*.sh", "attrs": ["text", "eol=lf"]}]

        self.assertEqual(build_gitattributes_gaps(files, existing_rules), [])

    def test_reports_uncovered_file_with_signal(self):
        files = [{"path": "deploy.patch", "mode": "100644", "has_shebang": False, "is_binary": False}]

        gaps = build_gitattributes_gaps(files, existing_rules=[])

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["path"], "deploy.patch")
        self.assertEqual(gaps[0]["suggested_attrs"], ["text", "eol=lf", "-diff"])

    def test_never_contradicts_an_existing_rule_even_if_classify_would_differ(self):
        # existing_rules covers run.sh with a DIFFERENT rule than classify_file would
        # suggest -- coverage wins; this file must not appear as a gap.
        files = [{"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False}]
        existing_rules = [{"pattern": "*.sh", "attrs": ["-text"]}]

        self.assertEqual(build_gitattributes_gaps(files, existing_rules), [])

    def test_a_catchall_text_auto_rule_fully_covers_an_ordinary_shebang_file(self):
        # Regression: this repo's OWN .gitattributes starts with exactly this
        # rule. Under a naive "any pattern matches" coverage check, it would
        # suppress every single gap in the whole repo, forever.
        files = [{"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False}]
        existing_rules = [{"pattern": "*", "attrs": ["text=auto", "eol=lf"]}]

        self.assertEqual(build_gitattributes_gaps(files, existing_rules), [])

    def test_a_catchall_text_auto_rule_still_leaves_a_partial_gap_for_diff(self):
        # The issue's own cited precedent (#9): *.patch needed -diff on top
        # of the repo's pre-existing `* text=auto eol=lf` catchall, because
        # the catchall addresses text/eol but says nothing about diff.
        files = [{"path": "deploy.patch", "mode": "100644", "has_shebang": False, "is_binary": False}]
        existing_rules = [{"pattern": "*", "attrs": ["text=auto", "eol=lf"]}]

        gaps = build_gitattributes_gaps(files, existing_rules)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["path"], "deploy.patch")
        self.assertEqual(gaps[0]["suggested_attrs"], ["-diff"])

    def test_eol_is_not_flagged_as_missing_when_an_existing_rule_already_marks_the_path_binary(self):
        # If an existing rule already says -text for this path, "eol" is
        # moot (git ignores eol on a -text path) -- it must never be
        # suggested on its own, which would read as contradicting the
        # existing -text rule.
        files = [{"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False}]
        existing_rules = [{"pattern": "*.sh", "attrs": ["-text"]}]

        self.assertEqual(build_gitattributes_gaps(files, existing_rules), [])


class BuildExecBitGapsTests(unittest.TestCase):
    def test_reports_only_files_with_drift(self):
        files = [
            {"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False},
            {"path": "notes.txt", "mode": "100644", "has_shebang": False, "is_binary": False},
        ]

        gaps = build_exec_bit_gaps(files)

        self.assertEqual(gaps, [{"path": "run.sh", "drift": "missing"}])


if __name__ == "__main__":
    unittest.main()
