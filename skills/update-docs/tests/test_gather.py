"""Tests for the gather() entrypoint that wires repo-type resolution,
doc-scope resolution (diff/range/whole-repo), generated-doc detection,
and the three optional checkers into one call -- the single "run this
first" step before any agent judgment about whether a doc's claim is
actually missing, incorrect or stale. Uses real git repos, not mocks.

Run from skills/update-docs/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.gather import gather


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


def _commit(root: Path, files: dict, message: str) -> None:
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _never_sync(cache_dir, template_path, run=None):
    """Stand-in for ensure_builtin_vale_config: pretend the vale sync
    always fails (no network), so these tests never depend on it."""
    return None


class GatherTests(unittest.TestCase):
    def test_diff_scope_only_checks_docs_the_diff_actually_touched(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            _init_repo(root)
            _commit(root, {"README.md": "v1", "docs/guide.md": "v1", "src/app.py": "v1"}, "first")
            (builtin_dir / "generic.md").write_text("# generic guide\n", encoding="utf-8")
            (root / "docs" / "guide.md").write_text("v2 (uncommitted)", encoding="utf-8")
            (root / "src" / "app.py").write_text("v2 (uncommitted)", encoding="utf-8")

            result = gather(root, scope="diff", home=home, builtin_types_dir=builtin_dir, ensure_vale=_never_sync)

            self.assertEqual(result["scope"], "diff")
            self.assertEqual(set(result["changed_files"]), {"docs/guide.md", "src/app.py"})
            self.assertEqual(result["changed_doc_files"], ["docs/guide.md"])
            self.assertEqual(result["docs_in_scope"], ["docs/guide.md"])
            self.assertEqual(set(result["all_doc_files"]), {"README.md", "docs/guide.md"})

    def test_repo_scope_checks_every_tracked_doc(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            _init_repo(root)
            _commit(root, {"README.md": "v1", "docs/guide.md": "v1", "CHANGELOG.md": "v1"}, "first")
            (builtin_dir / "generic.md").write_text("# generic guide\n", encoding="utf-8")

            result = gather(root, scope="repo", home=home, builtin_types_dir=builtin_dir, ensure_vale=_never_sync)

            self.assertEqual(result["scope"], "repo")
            self.assertEqual(set(result["docs_in_scope"]), {"README.md", "docs/guide.md"})
            self.assertNotIn("CHANGELOG.md", result["docs_in_scope"])  # Rule 6: hands off other records

    def test_a_generated_doc_in_scope_is_flagged(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            _init_repo(root)
            _commit(
                root,
                {"README.md": "<!-- AUTO-GENERATED FILE. DO NOT EDIT. -->\n# API\n"},
                "first",
            )
            (builtin_dir / "generic.md").write_text("# generic guide\n", encoding="utf-8")

            result = gather(root, scope="repo", home=home, builtin_types_dir=builtin_dir, ensure_vale=_never_sync)

            self.assertEqual(result["generated_docs"], ["README.md"])

    def test_resolves_the_repo_type_guide(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            _init_repo(root)
            _commit(root, {"go.mod": "module example.com/x\n", "README.md": "v1"}, "first")
            (builtin_dir / "go.md").write_text("# builtin go doc guide\n", encoding="utf-8")

            result = gather(root, scope="repo", home=home, builtin_types_dir=builtin_dir, ensure_vale=_never_sync)

            self.assertEqual(result["repo_type"]["guide"], "# builtin go doc guide\n")

    def test_no_docs_in_scope_skips_the_optional_checks_without_erroring(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            _init_repo(root)
            _commit(root, {"src/app.py": "v1"}, "first")
            (builtin_dir / "generic.md").write_text("# generic guide\n", encoding="utf-8")
            (root / "src" / "app.py").write_text("v2 (uncommitted)", encoding="utf-8")

            result = gather(root, scope="diff", home=home, builtin_types_dir=builtin_dir, ensure_vale=_never_sync)

            self.assertEqual(result["docs_in_scope"], [])
            self.assertTrue(result["checks"]["markdownlint"]["passed"])
            self.assertFalse(result["checks"]["markdownlint"]["ran"])
            self.assertTrue(result["checks"]["lychee"]["passed"])
            self.assertTrue(result["checks"]["vale"]["passed"])

    def test_range_scope_uses_the_given_base_instead_of_the_working_tree(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as builtin_dir:
            root, home, builtin_dir = Path(root), Path(home), Path(builtin_dir)
            _init_repo(root)
            _commit(root, {"README.md": "v1"}, "first")
            _run(["git", "tag", "v1.0.0"], root)
            _commit(root, {"README.md": "v2", "docs/guide.md": "new"}, "second")
            (builtin_dir / "generic.md").write_text("# generic guide\n", encoding="utf-8")

            result = gather(
                root, scope="range", base="v1.0.0", head="HEAD",
                home=home, builtin_types_dir=builtin_dir, ensure_vale=_never_sync,
            )

            self.assertEqual(set(result["changed_doc_files"]), {"README.md", "docs/guide.md"})

    def test_an_invalid_scope_raises(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                gather(Path(root), scope="bogus")


if __name__ == "__main__":
    unittest.main()
