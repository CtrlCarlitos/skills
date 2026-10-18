import tempfile
import unittest
from pathlib import Path
from scripts.workspace import child_dir, resolve_workspace

class ResolveWorkspaceTests(unittest.TestCase):
    def test_creates_the_full_structure_when_nothing_exists_yet(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            self.assertTrue((workspace / "children").is_dir())
            self.assertTrue((workspace / "sources" / "mineducyt").is_dir())
            self.assertTrue((workspace / "sources" / "santillana").is_dir())
            self.assertTrue((workspace / "assets").is_dir())

    def test_is_safe_to_call_again_on_an_existing_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "family"
            resolve_workspace(path)
            (path / "children" / "marker.txt").write_text("keep me", encoding="utf-8")

            resolve_workspace(path)

            self.assertEqual((path / "children" / "marker.txt").read_text(encoding="utf-8"), "keep me")

class ChildDirTests(unittest.TestCase):
    def test_creates_a_childs_partition(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = child_dir(workspace, "mateo")

            self.assertEqual(result, workspace / "children" / "mateo")
            self.assertTrue((result / "subjects").is_dir())

    def test_resolving_an_existing_child_again_does_not_clobber_their_data(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            first = child_dir(workspace, "mateo")
            (first / "subjects" / "note.txt").write_text("existing progress", encoding="utf-8")

            second = child_dir(workspace, "mateo")

            self.assertEqual(first, second)
            self.assertEqual((second / "subjects" / "note.txt").read_text(encoding="utf-8"), "existing progress")
