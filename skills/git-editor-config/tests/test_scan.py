"""Tests for scan_tracked_files. Uses a real local git repo built in a tmp
dir, not mocked subprocess output -- this is about correctly parsing git's
own `ls-files -s` mode-bit output, which is too easy to get subtly wrong
against hand-rolled fixture text.

Run from skills/git-editor-config/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.scan import scan_tracked_files


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


class ScanTrackedFilesTests(unittest.TestCase):
    def test_scans_a_real_repo_reporting_mode_shebang_and_binary(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "run.sh").write_text("#!/bin/bash\necho hi\n", encoding="utf-8")
            (repo / "notes.txt").write_text("plain text\n", encoding="utf-8")
            (repo / "photo.png").write_bytes(b"\x89PNG\x00\x01\x02binarydata")
            _run(["git", "add", "-A"], repo)
            (repo / "run.sh").chmod(0o755)
            _run(["git", "update-index", "--chmod=+x", "run.sh"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            files = {f["path"]: f for f in scan_tracked_files(repo)}

            self.assertTrue(files["run.sh"]["has_shebang"])
            self.assertEqual(files["run.sh"]["mode"], "100755")
            self.assertFalse(files["notes.txt"]["has_shebang"])
            self.assertFalse(files["notes.txt"]["is_binary"])
            self.assertTrue(files["photo.png"]["is_binary"])


if __name__ == "__main__":
    unittest.main()
