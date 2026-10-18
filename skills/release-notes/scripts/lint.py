"""Optional markdownlint-cli2 wrapper: a globally installed binary wins,
`npx` is the fallback when only Node tooling is present, and no linter
available means the lint step is skipped -- it is never a hard dependency
and never a hard failure on its own absence.
"""
import platform
import shutil
import subprocess


def find_linter(which=shutil.which) -> list[str] | None:
    if which("markdownlint-cli2"):
        return ["markdownlint-cli2"]
    if which("npx"):
        return ["npx", "--yes", "markdownlint-cli2"]
    return None


def lint_file(
    path: str,
    config_path: str | None = None,
    which=shutil.which,
    run=subprocess.run,
    system=platform.system,
) -> dict:
    """Returns {"ran": bool, "passed": bool, "output": str}. ran=False
    (no linter available) is always reported as passed=True -- an absent
    optional tool is not a lint failure."""
    linter = find_linter(which=which)
    if linter is None:
        return {"ran": False, "passed": True, "output": ""}

    args = list(linter)
    if config_path is not None:
        args.extend(["--config", config_path])
    args.append(path)

    # markdownlint-cli2 and npx are .cmd shims on Windows; CreateProcess
    # can't launch those directly without going through the shell --
    # confirmed live on windows-latest CI (WinError 2, FileNotFoundError).
    result = run(args, capture_output=True, text=True, shell=(system() == "Windows"))
    return {
        "ran": True,
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }
