"""Optional markdownlint-cli2 wrapper: an installed binary wins, `npx` is
the fallback when only Node tooling is present, and no linter available
means the check is skipped -- never a hard dependency, never a hard
failure on its own absence.
"""
import platform
import shutil
import subprocess


def find_markdownlint(which=shutil.which) -> list[str] | None:
    if which("markdownlint-cli2"):
        return ["markdownlint-cli2"]
    if which("npx"):
        return ["npx", "--yes", "markdownlint-cli2"]
    return None


def check_markdown(
    paths: str | list[str],
    config_path: str | None = None,
    cwd: str | None = None,
    which=shutil.which,
    run=subprocess.run,
    system=platform.system,
) -> dict:
    """Returns {"ran": bool, "passed": bool, "output": str}. ran=False
    is always reported as passed=True -- an absent optional tool is not a
    check failure. `paths` may be a single path or several -- confirmed
    live that markdownlint-cli2 accepts multiple files in one call.
    `cwd` should be the repo being audited when `config_path` is omitted,
    so markdownlint-cli2's own auto-discovery finds THAT repo's config
    (Rule 8: use what the repo already has) instead of whatever directory
    this process happens to be running from."""
    cmd = find_markdownlint(which=which)
    if cmd is None:
        return {"ran": False, "passed": True, "output": ""}

    args = list(cmd)
    if config_path is not None:
        args.extend(["--config", config_path])
    args.extend([paths] if isinstance(paths, str) else paths)

    # markdownlint-cli2 and npx are .cmd shims on Windows; CreateProcess
    # can't launch those directly without going through the shell --
    # confirmed live on windows-latest CI for release-notes' own lint.py.
    result = run(args, capture_output=True, text=True, shell=(system() == "Windows"), cwd=cwd)
    return {
        "ran": True,
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr,
    }
