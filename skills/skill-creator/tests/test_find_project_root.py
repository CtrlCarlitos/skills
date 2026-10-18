"""Regression tests for patch 0003 (--project-root / find_project_root()).

find_project_root() mimics how Claude Code discovers its project root, by
walking up from cwd looking for a `.claude/` directory. Run outside a repo
(e.g. from a subagent whose cwd isn't the project), it lands wherever cwd
happens to be instead of the real project — which is exactly what
--project-root exists to override.

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.run_eval import find_project_root


class FindProjectRootTests(unittest.TestCase):
    def _make_dir(self) -> Path:
        """A temp dir cleaned up via addCleanup, never a `with` block.

        Windows can't remove a directory that is still the process's cwd
        (POSIX allows this; Windows doesn't), so cwd must be restored
        before cleanup runs. addCleanup runs LIFO, so as long as _chdir()
        is called after _make_dir() for the same directory, the chdir-back
        registered by _chdir() fires before this rmtree.
        """
        path = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)
        return path

    def _chdir(self, path: Path) -> None:
        original = Path.cwd()
        os.chdir(path)
        self.addCleanup(os.chdir, original)

    def test_finds_nearest_ancestor_with_dot_claude(self):
        root = self._make_dir()
        (root / ".claude").mkdir()
        nested = root / "a" / "b" / "c"
        nested.mkdir(parents=True)
        self._chdir(nested)

        self.assertEqual(find_project_root(), root)

    def test_falls_back_to_cwd_when_no_dot_claude_found(self):
        root = self._make_dir()
        nested = root / "a" / "b"
        nested.mkdir(parents=True)
        self._chdir(nested)

        # No .claude/ anywhere above `nested` inside this isolated tree,
        # so the walk reaches the real filesystem root. It must not
        # raise, and must land on an ancestor of (or equal to) cwd.
        found = find_project_root()
        self.assertIn(found, [nested, *nested.parents])

    def test_project_root_flag_overrides_discovery(self):
        """main()'s `Path(args.project_root).resolve() if args.project_root else
        find_project_root()` must prefer an explicit --project-root over
        walking up from cwd, even when cwd has its own (different) .claude/.
        """
        cwd_root = self._make_dir()
        explicit_root = self._make_dir()
        (cwd_root / ".claude").mkdir()
        self._chdir(cwd_root)

        args_project_root = str(explicit_root)
        resolved = Path(args_project_root).resolve() if args_project_root else find_project_root()

        self.assertEqual(resolved, explicit_root)
        self.assertNotEqual(resolved, cwd_root)


if __name__ == "__main__":
    unittest.main()
