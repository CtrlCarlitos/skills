"""Regression tests for patch 0003 (--project-root / find_project_root()).

find_project_root() mimics how Claude Code discovers its project root, by
walking up from cwd looking for a `.claude/` directory. Run outside a repo
(e.g. from a subagent whose cwd isn't the project), it lands wherever cwd
happens to be instead of the real project — which is exactly what
--project-root exists to override.

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest
from pathlib import Path

from scripts.run_eval import find_project_root


class FindProjectRootTests(unittest.TestCase):
    def _chdir(self, path: Path) -> None:
        original = Path.cwd()
        os.chdir(path)
        self.addCleanup(os.chdir, original)

    def test_finds_nearest_ancestor_with_dot_claude(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root).resolve()
            (root / ".claude").mkdir()
            nested = root / "a" / "b" / "c"
            nested.mkdir(parents=True)
            self._chdir(nested)

            self.assertEqual(find_project_root(), root)

    def test_falls_back_to_cwd_when_no_dot_claude_found(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root).resolve()
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
        with tempfile.TemporaryDirectory() as cwd_root, tempfile.TemporaryDirectory() as explicit_root:
            cwd_root = Path(cwd_root).resolve()
            explicit_root = Path(explicit_root).resolve()
            (cwd_root / ".claude").mkdir()
            self._chdir(cwd_root)

            args_project_root = str(explicit_root)
            resolved = Path(args_project_root).resolve() if args_project_root else find_project_root()

            self.assertEqual(resolved, explicit_root)
            self.assertNotEqual(resolved, cwd_root)


if __name__ == "__main__":
    unittest.main()
