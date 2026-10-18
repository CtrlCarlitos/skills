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

    def test_a_large_real_text_file_scanned_through_the_real_function_is_not_binary(self):
        # Review Focus #2, exercised through the real function rather than a
        # hand-built dict -- the earlier version of this test passed
        # is_binary=False straight into classify_file, which never actually
        # ran the sniff.
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "bundle.min.js").write_text("var x=1;" * 5000, encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            files = {f["path"]: f for f in scan_tracked_files(repo)}

            self.assertFalse(files["bundle.min.js"]["is_binary"])

    def test_non_ascii_filename_does_not_crash(self):
        # Asserted by shape, not by an exact non-ASCII literal match: a
        # filesystem/git combination is free to normalize "é" differently
        # (precomposed vs. a combining accent) between where this test file
        # is written and where it runs, which would make a hardcoded-literal
        # comparison fail despite scan_tracked_files behaving correctly.
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "café.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            files = scan_tracked_files(repo)

            self.assertEqual(len(files), 1)
            self.assertTrue(files[0]["path"].endswith(".sh"))
            self.assertTrue(files[0]["has_shebang"])
            self.assertTrue(files[0]["has_shebang"])

    def test_a_tracked_file_deleted_from_the_working_tree_does_not_crash(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "gone.txt").write_text("bye\n", encoding="utf-8")
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)
            (repo / "gone.txt").unlink()

            files = {f["path"]: f for f in scan_tracked_files(repo)}

            self.assertFalse(files["gone.txt"]["has_shebang"])
            self.assertFalse(files["gone.txt"]["is_binary"])

    def test_a_submodule_gitlink_entry_does_not_crash(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "vendor_sub").mkdir()
            _run(["git", "update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},vendor_sub"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            files = {f["path"]: f for f in scan_tracked_files(repo)}

            self.assertFalse(files["vendor_sub"]["has_shebang"])
            self.assertFalse(files["vendor_sub"]["is_binary"])

    def test_a_symlink_to_a_directory_does_not_crash(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            (repo / "real_dir").mkdir()
            (repo / "link_to_dir").symlink_to("real_dir", target_is_directory=True)
            _run(["git", "add", "-A"], repo)
            _run(["git", "commit", "-q", "-m", "init"], repo)

            files = {f["path"]: f for f in scan_tracked_files(repo)}

            self.assertFalse(files["link_to_dir"]["has_shebang"])
            self.assertFalse(files["link_to_dir"]["is_binary"])


if __name__ == "__main__":
    unittest.main()
