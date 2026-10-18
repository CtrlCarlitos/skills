import unittest

from scripts.classify import classify_file


class ClassifyFileTests(unittest.TestCase):
    def test_shebang_file_suggests_text_eol_lf(self):
        result = classify_file({"path": "run.sh", "mode": "100755", "has_shebang": True, "is_binary": False})

        self.assertEqual(result["attrs"], ["text", "eol=lf"])

    def test_patch_extension_suggests_text_eol_lf_no_diff(self):
        result = classify_file({"path": "vendor/foo.patch", "mode": "100644", "has_shebang": False, "is_binary": False})

        self.assertEqual(result["attrs"], ["text", "eol=lf", "-diff"])

    def test_binary_signal_suggests_no_text_no_diff(self):
        result = classify_file({"path": "logo.png", "mode": "100644", "has_shebang": False, "is_binary": True})

        self.assertEqual(result["attrs"], ["-text", "-diff"])

    def test_large_plain_text_file_is_not_misclassified_as_binary(self):
        # No null byte in the scanned chunk -- is_binary is False, as scan.py would report.
        result = classify_file({"path": "bundle.min.js", "mode": "100644", "has_shebang": False, "is_binary": False})

        self.assertIsNone(result)

    def test_ordinary_file_with_no_signal_returns_none(self):
        result = classify_file({"path": "README.md", "mode": "100644", "has_shebang": False, "is_binary": False})

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
