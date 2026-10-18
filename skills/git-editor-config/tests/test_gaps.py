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
