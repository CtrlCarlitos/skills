"""Build and run the repository-owned local-validation contract: parse
what CI actually runs, map each runnable step to the exact local command
(no separate local/remote check logic), flag non-runnable steps (a
`uses:` action step, e.g. `actions/checkout`) as CI-only with a reason
instead of silently dropping them, and classify `continue-on-error`
steps as optional rather than required.
"""
import platform
import subprocess

import yaml


def parse_ci_steps(workflow_text: str) -> list[dict]:
    """One entry per step across every job in the workflow:
    {"job", "step_name", "run", "uses", "working_directory",
    "continue_on_error", "runs_on"}.
    """
    data = yaml.safe_load(workflow_text)
    entries = []
    for job_name, job in data.get("jobs", {}).items():
        for step in job.get("steps", []):
            entries.append({
                "job": job_name,
                "step_name": step.get("name"),
                "run": step.get("run"),
                "uses": step.get("uses"),
                "working_directory": step.get("working-directory"),
                "continue_on_error": bool(step.get("continue-on-error", False)),
                "runs_on": job.get("runs-on"),
            })
    return entries


def build_local_validation_contract(steps: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (contract, ci_only). `contract` entries are
    {"job", "step_name", "command", "working_directory", "status"}
    ("required" or "optional"). `ci_only` entries are the original step
    dicts plus a "reason" -- a `uses:` action step has no local
    equivalent at all, so it's reported, never silently dropped."""
    contract = []
    ci_only = []
    for step in steps:
        if step["run"] is None:
            ci_only.append({**step, "reason": f"GitHub Action step ({step['uses']}), not a local command"})
            continue
        contract.append({
            "job": step["job"],
            "step_name": step["step_name"],
            "command": step["run"],
            "working_directory": step["working_directory"],
            "status": "optional" if step["continue_on_error"] else "required",
        })
    return contract, ci_only


def run_contract(contract: list[dict], repo_root, run=subprocess.run, system=platform.system) -> list[dict]:
    """Runs each entry's command through the shell (these are literal
    GitHub Actions `run:` blocks -- single or multi-line shell scripts,
    not argv lists) from its declared working directory, relative to
    repo_root. Returns one result per entry: the original fields plus
    "passed", "returncode", "output".

    On Windows, routes through `pwsh` explicitly rather than
    subprocess's own shell=True default (cmd.exe) -- confirmed live on
    windows-latest CI that GitHub Actions' `run:` steps execute through
    PowerShell there, not cmd, so reproducing them through cmd.exe can
    silently run different (or invalid) syntax than CI actually ran."""
    is_windows = system() == "Windows"
    results = []
    for entry in contract:
        cwd = repo_root / entry["working_directory"] if entry["working_directory"] else repo_root
        if is_windows:
            result = run(
                ["pwsh", "-NoLogo", "-NoProfile", "-Command", entry["command"]],
                cwd=cwd, capture_output=True, text=True,
            )
        else:
            result = run(entry["command"], shell=True, cwd=cwd, capture_output=True, text=True)
        results.append({
            **entry,
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "output": result.stdout + result.stderr,
        })
    return results
