"""Optional lychee link-checker wrapper. Unlike markdownlint-cli2, lychee
is a native binary with no universal package-manager fallback (no npx
equivalent) -- "not installed" just means the check is skipped, never a
hard dependency or a hard failure.
"""
import json
import shutil
import subprocess


def find_linkchecker(which=shutil.which) -> list[str] | None:
    if which("lychee"):
        return ["lychee"]
    return None


def check_links(
    paths: str | list[str],
    config_path: str | None = None,
    cwd: str | None = None,
    which=shutil.which,
    run=subprocess.run,
) -> dict:
    """Returns {"ran": bool, "passed": bool, "broken": [...], "output": str}.
    Each broken entry is {"file", "url", "line", "status"}. ran=False is
    always reported as passed=True -- an absent optional tool is not a
    check failure. `paths` may be a single path or several -- confirmed
    live that lychee accepts multiple files in one call. `cwd` should be
    the repo being audited when `config_path` is omitted, so lychee's own
    auto-discovery of a `lychee.toml` finds THAT repo's config."""
    cmd = find_linkchecker(which=which)
    if cmd is None:
        return {"ran": False, "passed": True, "broken": [], "output": ""}

    args = list(cmd) + ["--format", "json"]
    if config_path is not None:
        args.extend(["--config", config_path])
    args.extend([paths] if isinstance(paths, str) else paths)

    result = run(args, capture_output=True, text=True, cwd=cwd)

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {"ran": True, "passed": False, "broken": [], "output": result.stdout + result.stderr}

    broken = [
        {"file": file, "url": entry["url"], "line": entry["span"]["line"], "status": entry["status"]["text"]}
        for file, file_errors in data.get("error_map", {}).items()
        for entry in file_errors
    ]

    return {
        "ran": True,
        "passed": data.get("errors", 0) == 0,
        "broken": broken,
        "output": result.stdout + result.stderr,
    }
