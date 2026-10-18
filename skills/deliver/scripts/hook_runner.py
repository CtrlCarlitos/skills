"""Non-interactive CLI over validation_contract.py's existing
parse/build/run functions, for a git hook to call. Reuses that module's
logic unchanged -- this file adds only the "read the workflow file, print
a summary, pick an exit code" layer a hook needs that an interactive
agent invocation doesn't.
"""
import sys
from pathlib import Path

from scripts.validation_contract import build_local_validation_contract, parse_ci_steps, run_contract

_WORKFLOW_PATH = Path(".github") / "workflows" / "ci.yml"


def run_validation(repo_root: Path) -> int:
    workflow_file = Path(repo_root) / _WORKFLOW_PATH
    try:
        workflow_text = workflow_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"deliver hook: no {_WORKFLOW_PATH} found at {repo_root} -- nothing to validate against")
        return 1

    steps = parse_ci_steps(workflow_text)
    contract, _ci_only = build_local_validation_contract(steps)
    results = run_contract(contract, Path(repo_root))

    failed_required = False
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"deliver hook: [{status}] {result['step_name']} ({result['status']})")
        if not result["passed"] and result["status"] == "required":
            failed_required = True

    return 1 if failed_required else 0


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]) if argv else Path.cwd()
    return run_validation(repo_root)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
