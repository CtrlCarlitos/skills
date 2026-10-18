"""Tests for release-range resolution. Uses real local git repos built in
tmp dirs, not mocked subprocess output -- this is fundamentally about
correctly parsing git's actual behavior (git describe, shallow-clone
detection, "is this even a repo"), which is too easy to get subtly wrong
against hand-rolled fixture text.

Run from skills/release-notes/: python3 -m unittest discover -s tests
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.range import RangeError, resolve_range


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "x@x.com"], root)
    _run(["git", "config", "user.name", "x"], root)


def _commit(root: Path, message: str, filename: str = "file.txt") -> None:
    (root / filename).write_text(message, encoding="utf-8")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _tag(root: Path, name: str) -> None:
    _run(["git", "tag", name], root)


class ResolveRangeTests(unittest.TestCase):
    def test_raises_when_the_directory_is_not_a_git_repo_at_all(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(RangeError) as ctx:
                resolve_range(Path(root))

            self.assertIn("not a git repository", str(ctx.exception).lower())

    def test_raises_when_no_base_is_given_and_no_tag_exists(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "first commit")

            with self.assertRaises(RangeError) as ctx:
                resolve_range(root)

            self.assertIn("no tag", str(ctx.exception).lower())

    def test_resolves_the_previous_tag_as_base_when_none_given(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "first commit")
            _tag(root, "v1.0.0")
            _commit(root, "second commit")

            result = resolve_range(root)

            self.assertEqual(result["base"], "v1.0.0")
            self.assertEqual(result["head"], "HEAD")

    def test_an_explicit_base_is_used_without_resolving_a_tag(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "first commit")
            _tag(root, "v1.0.0")
            _commit(root, "second commit")
            _tag(root, "v2.0.0")
            _commit(root, "third commit")

            result = resolve_range(root, base="v1.0.0")

            self.assertEqual(result["base"], "v1.0.0")

    def test_raises_on_a_real_shallow_clone(self):
        with tempfile.TemporaryDirectory() as source_root, tempfile.TemporaryDirectory() as clone_parent:
            source_root = Path(source_root)
            _init_repo(source_root)
            _commit(source_root, "first commit")
            _tag(source_root, "v1.0.0")
            _commit(source_root, "second commit")

            clone_parent = Path(clone_parent)
            clone_root = clone_parent / "clone"
            # git silently ignores --depth for a plain local path (just does a
            # full clone); file:// is required to get a genuinely shallow one.
            _run(["git", "clone", "-q", "--depth", "1", f"file://{source_root}", str(clone_root)], clone_parent)

            with self.assertRaises(RangeError) as ctx:
                resolve_range(clone_root)

            self.assertIn("shallow", str(ctx.exception).lower())

    def test_resolves_head_to_its_actual_commit_sha(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            _init_repo(root)
            _commit(root, "first commit")
            _tag(root, "v1.0.0")
            _commit(root, "second commit")

            result = resolve_range(root)

            real_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
            ).stdout.strip()
            self.assertEqual(result["head_sha"], real_sha)


if __name__ == "__main__":
    unittest.main()
