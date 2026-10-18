"""Non-interactive CLI over validation_contract.py's existing
parse/build/run functions, for a git hook to call. Reuses that module's
logic unchanged -- this file adds only the "read the workflow file,
filter to what this machine can run, print a summary, pick an exit
code" layer a hook needs that an interactive agent invocation doesn't.

The installed hook invokes this as a bare script path
(`"$PY" "/abs/path/hook_runner.py" <repo_root>`), not as `-m
scripts.hook_runner` -- so `scripts.validation_contract` is not
importable as a package unless this file's own directory's parent is on
sys.path first. This insert must run before the import below, in every
invocation form (bare script, `-m`, or a normal package import from a
test), which is why it's unconditional at module scope, not inside an
`if __name__ == "__main__"` guard.
"""
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validation_contract import build_local_validation_contract, parse_ci_steps, run_contract

_WORKFLOW_PATH = Path(".github") / "workflows" / "ci.yml"

_RUNNER_KEYWORD_BY_PLATFORM = {
    "Linux": "ubuntu",
    "Windows": "windows",
    "Darwin": "macos",
}


def _matches_current_platform(runs_on: str | None, system: str) -> bool:
    keyword = _RUNNER_KEYWORD_BY_PLATFORM.get(system)
    if keyword is None or not runs_on:
        return True  # unknown platform or unspecified runs-on: never silently drop a job
    return keyword in runs_on.lower()


def run_validation(repo_root: Path, system=platform.system) -> int:
    workflow_file = Path(repo_root) / _WORKFLOW_PATH
    try:
        workflow_text = workflow_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"deliver hook: no {_WORKFLOW_PATH} found at {repo_root} -- nothing to validate against")
        return 1

    steps = parse_ci_steps(workflow_text)
    contract, _ci_only = build_local_validation_contract(steps)

    job_runs_on = {step["job"]: step["runs_on"] for step in steps}
    current_system = system()
    contract = [entry for entry in contract if _matches_current_platform(job_runs_on.get(entry["job"]), current_system)]

    results = run_contract(contract, Path(repo_root))

    failed_required = False
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"deliver hook: [{status}] {result['step_name']} ({result['status']})")
        if not result["passed"]:
            print(result["output"])
            if result["status"] == "required":
                failed_required = True

    return 1 if failed_required else 0


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]) if argv else Path.cwd()
    return run_validation(repo_root)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
