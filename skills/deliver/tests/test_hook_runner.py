"""Tests for hook_runner's non-interactive CLI over the existing
validation_contract functions. Real small git-repo fixtures built in tmp
dirs, each with a real .github/workflows/ci.yml -- not mocked subprocess
output, since this is about actually running real shell commands.

Run from skills/deliver/: python3 -m unittest discover -s tests
"""
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.hook_runner import run_validation

_HOOK_RUNNER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "hook_runner.py"

# This repo's CI runs these same tests on all three OSes. A job fixture must
# default to THIS platform's own conventional runs-on value, or hook_runner's
# own (correct) current-OS filtering silently excludes it on macOS/Windows CI
# -- which several of these tests' expected results would then satisfy for
# the wrong reason (filtered-out looks identical to "ran and matched") rather
# than visibly failing. Confirmed live: this exact bug shipped and was caught
# by this project's own CI on the first real PR for this feature.
_CURRENT_RUNS_ON = {"Linux": "ubuntu-latest", "Windows": "windows-latest", "Darwin": "macos-latest"}[platform.system()]


def _py_job(job_name: str, code: str, continue_on_error: bool = False, runs_on: str | None = None) -> str:
    runs_on = runs_on or _CURRENT_RUNS_ON
    coe = "        continue-on-error: true\n" if continue_on_error else ""
    return (
        f"  {job_name}:\n    runs-on: {runs_on}\n    steps:\n"
        f'      - name: {job_name}\n{coe}        run: |\n          {sys.executable} -c "{code}"\n'
    )


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=root, check=True, capture_output=True)


def _write_workflow(root: Path, jobs_yaml: str) -> None:
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(f"jobs:\n{jobs_yaml}", encoding="utf-8")


class RunValidationTests(unittest.TestCase):
    def test_returns_zero_when_the_only_required_step_passes(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_job("ok", "import sys; sys.exit(0)"))

            self.assertEqual(run_validation(repo), 0)

    def test_returns_one_when_a_required_step_fails(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_job("bad", "import sys; sys.exit(1)"))

            self.assertEqual(run_validation(repo), 1)

    def test_returns_zero_when_only_an_optional_step_fails(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_job("flaky", "import sys; sys.exit(1)", continue_on_error=True))

            self.assertEqual(run_validation(repo), 0)

    def test_returns_one_with_a_clear_message_when_the_workflow_file_is_missing(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)

            self.assertEqual(run_validation(repo), 1)

    def test_skips_jobs_whose_runs_on_does_not_match_the_current_platform(self):
        # A job pinned to an OS this test isn't running on must never block a
        # commit here -- the hook's whole point is validating what THIS
        # machine can actually run, not every job in the matrix.
        import platform
        other_os = {"Linux": "windows-latest", "Windows": "ubuntu-latest", "Darwin": "ubuntu-latest"}[platform.system()]
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            jobs = _py_job("other_platform_bad", "import sys; sys.exit(1)", runs_on=other_os)
            _write_workflow(repo, jobs)

            self.assertEqual(run_validation(repo), 0)

    def test_prints_the_failing_steps_output_not_just_pass_fail(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_job("bad", "print('a-distinctive-marker'); import sys; sys.exit(1)"))

            import io
            import contextlib

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run_validation(repo)

            self.assertIn("a-distinctive-marker", buf.getvalue())


class HookRunnerCliSubprocessTests(unittest.TestCase):
    def test_runs_as_a_bare_script_not_just_as_a_package_module(self):
        # This is exactly how the installed hook invokes it: a bare absolute
        # path, not `python -m scripts.hook_runner` from inside skills/deliver
        # -- a prior version of this file only ever imported run_validation
        # in-process, which missed that the real invocation form couldn't
        # even import validation_contract.
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_job("ok", "import sys; sys.exit(0)"))

            result = subprocess.run(
                [sys.executable, str(_HOOK_RUNNER_PATH), str(repo)],
                capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_bare_script_invocation_fails_the_exit_code_on_a_bad_step(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            _init_repo(repo)
            _write_workflow(repo, _py_job("bad", "import sys; sys.exit(1)"))

            result = subprocess.run(
                [sys.executable, str(_HOOK_RUNNER_PATH), str(repo)],
                capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 1, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
