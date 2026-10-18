"""Tests for hook_runner's non-interactive CLI over the existing
validation_contract functions. Real small git-repo fixtures built in tmp
dirs, each with a real .github/workflows/ci.yml -- not mocked subprocess
output, since this is about actually running real shell commands.

Run from skills/deliver/: python3 -m unittest discover -s tests
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.hook_runner import run_validation


def _py_step(name: str, code: str, continue_on_error: bool = False) -> str:
    coe = "        continue-on-error: true\n" if continue_on_error else ""
    return f'      - name: {name}\n{coe}        run: |\n          {sys.executable} -c "{code}"\n'


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=root, check=True, capture_output=True)


def _write_workflow(root: Path, steps_yaml: str) -> None:
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        f"jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n{steps_yaml}",
        encoding="utf-8",
    )


class RunValidationTests(unittest.TestCase):
    def test_returns_zero_when_the_only_required_step_passes(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_step("ok", "import sys; sys.exit(0)"))

            self.assertEqual(run_validation(repo), 0)

    def test_returns_one_when_a_required_step_fails(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_step("bad", "import sys; sys.exit(1)"))

            self.assertEqual(run_validation(repo), 1)

    def test_returns_zero_when_only_an_optional_step_fails(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_step("flaky", "import sys; sys.exit(1)", continue_on_error=True))

            self.assertEqual(run_validation(repo), 0)

    def test_returns_one_with_a_clear_message_when_the_workflow_file_is_missing(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)

            self.assertEqual(run_validation(repo), 1)


if __name__ == "__main__":
    unittest.main()
