"""Regression test for patch 0002 (explicit UTF-8 file I/O everywhere).

On a non-UTF-8 locale (e.g. cp1252), `open()`/`read_text()`/`write_text()`
without an explicit encoding fall back to the platform's preferred encoding
and crash on non-ASCII content (the original bug: a report containing U+2717
raised UnicodeEncodeError). Rather than depend on actually running under a
different locale, this statically scans the vendored source for text I/O
calls missing `encoding="utf-8"`, so a future edit can't silently reintroduce
the bug this patch fixed.

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import re
import unittest
from pathlib import Path

SKILL_CREATOR_ROOT = Path(__file__).resolve().parent.parent

# Text-mode open()/read_text()/write_text() calls that must carry an explicit
# encoding. Binary mode ("rb"/"wb") and calls that already pass encoding=
# are not flagged.
TEXT_IO_CALL = re.compile(r"\.read_text\(|\.write_text\(|(?<![.\w])open\(")


def _calls_missing_encoding(source: str) -> list[str]:
    missing = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if "encoding=" in line:
            continue
        if "rb" in line or "wb" in line or "ab" in line:
            # Binary mode: encoding is meaningless, not a bug.
            if re.search(r'open\([^)]*["\'][rwa]b["\']', line):
                continue
        for match in TEXT_IO_CALL.finditer(line):
            missing.append(f"{lineno}: {line.strip()}")
    return missing


class DetectorSelfTests(unittest.TestCase):
    """The scanner itself must actually catch what it claims to catch."""

    def test_flags_read_text_without_encoding(self):
        offenders = _calls_missing_encoding('content = path.read_text()\n')
        self.assertEqual(len(offenders), 1)

    def test_flags_bare_open_without_encoding(self):
        offenders = _calls_missing_encoding('with open(path) as f:\n')
        self.assertEqual(len(offenders), 1)

    def test_does_not_flag_calls_with_explicit_encoding(self):
        offenders = _calls_missing_encoding('content = path.read_text(encoding="utf-8")\n')
        self.assertEqual(offenders, [])

    def test_does_not_flag_binary_mode_open(self):
        offenders = _calls_missing_encoding('with open(path, "rb") as f:\n')
        self.assertEqual(offenders, [])

    def test_does_not_flag_unrelated_dot_open_methods(self):
        offenders = _calls_missing_encoding('webbrowser.open(str(live_report_path))\n')
        self.assertEqual(offenders, [])


class Utf8FileIoTests(unittest.TestCase):
    def test_no_text_io_call_is_missing_an_explicit_encoding(self):
        offenders = {}
        for py_file in sorted(SKILL_CREATOR_ROOT.rglob("*.py")):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue
            source = py_file.read_text(encoding="utf-8")
            calls = _calls_missing_encoding(source)
            if calls:
                offenders[str(py_file.relative_to(SKILL_CREATOR_ROOT))] = calls

        self.assertEqual(
            offenders,
            {},
            "Found text I/O calls without an explicit encoding= (see patch "
            "0002-utf8-file-io.patch for why this matters)",
        )


if __name__ == "__main__":
    unittest.main()
