import unittest

from scripts.exec_bit import exec_bit_drift


class ExecBitDriftTests(unittest.TestCase):
    def test_shebang_without_exec_bit_is_missing(self):
        drift = exec_bit_drift({"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False})

        self.assertEqual(drift, "missing")

    def test_shebang_with_exec_bit_is_not_flagged(self):
        drift = exec_bit_drift({"path": "run.sh", "mode": "100755", "has_shebang": True, "is_binary": False})

        self.assertIsNone(drift)

    def test_exec_bit_on_known_non_executable_extension_is_unexpected(self):
        drift = exec_bit_drift({"path": "notes.md", "mode": "100755", "has_shebang": False, "is_binary": False})

        self.assertEqual(drift, "unexpected")

    def test_exec_bit_without_shebang_on_ambiguous_extension_is_not_flagged(self):
        # .py and .sh are commonly executable by convention even without a shebang in some
        # repos -- conservative by design, per the plan's Review Focus: never flag removal
        # for these.
        self.assertIsNone(exec_bit_drift({"path": "tool.py", "mode": "100755", "has_shebang": False, "is_binary": False}))
        self.assertIsNone(exec_bit_drift({"path": "tool.sh", "mode": "100755", "has_shebang": False, "is_binary": False}))


if __name__ == "__main__":
    unittest.main()
