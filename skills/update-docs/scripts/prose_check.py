"""Optional vale prose-style wrapper. Unlike markdownlint-cli2/lychee,
vale needs an actual config to do anything -- with none, it errors ("no
config file found") instead of silently passing. Per the issue: the
repo's own .vale.ini wins; otherwise this skill's built-in config, which
declares the Google developer documentation style package and is synced
with `vale sync` on first use (confirmed live: this works over the
network, no vendored style files needed).
"""
import json
import shutil
import subprocess
from pathlib import Path


def find_vale(which=shutil.which) -> list[str] | None:
    if which("vale"):
        return ["vale"]
    return None


def resolve_vale_config(repo_root: Path, builtin_config_path: Path) -> Path:
    repo_config = repo_root / ".vale.ini"
    if repo_config.is_file():
        return repo_config
    return builtin_config_path


def ensure_builtin_styles_synced(config_dir: Path, run=subprocess.run) -> bool:
    """Runs `vale sync` in config_dir (where the built-in .vale.ini
    lives) unless its declared StylesPath already has content. Returns
    whether the styles are now in place -- False means sync failed
    (e.g. no network), and the caller should treat prose-checking as
    unavailable rather than failing outright."""
    styles_dir = config_dir / "styles" / "Google"
    if styles_dir.is_dir() and any(styles_dir.iterdir()):
        return True

    result = run(["vale", "sync"], cwd=config_dir, capture_output=True, text=True)
    return result.returncode == 0 and styles_dir.is_dir()


def ensure_builtin_vale_config(cache_dir: Path, template_ini_path: Path, run=subprocess.run) -> Path | None:
    """Copies the skill's shipped .vale.ini template into a writable
    cache dir (next to where its styles get synced -- never into the
    skill's own installed/read-only directory) and syncs styles if
    they're not already there. Returns the usable config path, or None
    if syncing failed (e.g. no network) -- the caller should then treat
    prose-checking as unavailable rather than erroring."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    ini_path = cache_dir / ".vale.ini"
    if not ini_path.is_file():
        ini_path.write_text(template_ini_path.read_text(encoding="utf-8"), encoding="utf-8")

    if not ensure_builtin_styles_synced(cache_dir, run=run):
        return None
    return ini_path


def check_prose(
    paths: str | list[str],
    config_path: str,
    which=shutil.which,
    run=subprocess.run,
) -> dict:
    """Returns {"ran": bool, "passed": bool, "findings": [...], "output": str}.
    ran=False is always reported as passed=True -- an absent optional tool
    is not a check failure. A tool-level error (missing config, crash) is
    ran=True, passed=False, findings=[] -- distinct from "ran cleanly and
    found nothing to flag". `paths` may be a single path or several --
    confirmed live that vale accepts multiple files in one call."""
    cmd = find_vale(which=which)
    if cmd is None:
        return {"ran": False, "passed": True, "findings": [], "output": ""}

    args = list(cmd) + ["--output=JSON", "--config", config_path]
    args.extend([paths] if isinstance(paths, str) else paths)
    result = run(args, capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {"ran": True, "passed": False, "findings": [], "output": result.stdout + result.stderr}

    # vale's "no findings" JSON shape depends on how many files were
    # checked -- confirmed live: {} for one clean file, [] for several.
    # Only a dict can ever be the "Code"/"Path" tool-error shape or carry
    # per-file finding lists.
    if isinstance(data, list):
        findings = []
    elif "Code" in data and "Path" in data:
        return {"ran": True, "passed": False, "findings": [], "output": data.get("Text", result.stdout)}
    else:
        findings = [f for file_findings in data.values() for f in file_findings]
    return {
        "ran": True,
        "passed": len(findings) == 0,
        "findings": findings,
        "output": result.stdout + result.stderr,
    }
