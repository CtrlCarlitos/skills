#!/usr/bin/env python3
"""Open a generated artifact (e.g. an HTML file) using the best available
mechanism for the current environment, without ever losing the artifact,
hanging, or silently failing.

Creating the artifact already succeeded before this script runs; opening
it is a best-effort convenience layered on top, never a requirement. This
always prints the artifact's real path and exits 0 whether or not an
opener actually launched.

Usage: python3 open_artifact.py <path>
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def detect_environment(system: str, environ: dict, proc_version: str) -> str:
    """Classify the current host into one bucket this module can act on.

    One of: windows, wsl, devcontainer, macos, macos-headless,
    linux-desktop, linux-headless.

    Pure function over explicit inputs (not os.environ/platform.system()
    read directly) so the decision logic is testable without mocking.
    """
    if system == "Windows":
        return "windows"

    if system == "Darwin":
        is_headless_ssh = bool(environ.get("SSH_CONNECTION") or environ.get("SSH_TTY"))
        return "macos-headless" if is_headless_ssh else "macos"

    # Linux (WSL and devcontainers also report as Linux).
    is_container = bool(
        environ.get("REMOTE_CONTAINERS")
        or environ.get("CODESPACES")
        or environ.get("DEVCONTAINER")
    )
    if is_container:
        return "devcontainer"

    is_wsl = bool(environ.get("WSL_DISTRO_NAME")) or "microsoft" in proc_version.lower()
    if is_wsl:
        return "wsl"

    has_display = bool(environ.get("DISPLAY") or environ.get("WAYLAND_DISPLAY"))
    return "linux-desktop" if has_display else "linux-headless"


def opener_command(env: str, path: Path, which) -> list[str] | None:
    """The command to launch for this environment, or None.

    None means: no sensible opener exists here (headless SSH, a
    devcontainer, or a desktop tool that isn't actually installed). The
    artifact still exists either way -- this only decides whether to also
    try launching something. `which` is injected (ordinarily
    shutil.which) so availability is genuinely detected, not assumed.
    """
    if env == "windows":
        # Windows always has cmd.exe; no availability check needed.
        return ["cmd.exe", "/c", "start", "", str(path)]
    if env == "macos":
        # Real macOS always has `open`; no availability check needed.
        return ["open", str(path)]
    if env == "wsl":
        return ["wslview", str(path)] if which("wslview") else None
    if env == "linux-desktop":
        return ["xdg-open", str(path)] if which("xdg-open") else None
    # macos-headless, linux-headless, devcontainer: no opener attempt.
    return None


def try_open(cmd: list[str], popen=subprocess.Popen) -> bool:
    """Launch cmd without ever blocking on it or letting it raise.

    Fire-and-forget: never calls .wait()/.communicate(), so a GUI opener
    that doesn't exit on its own can't hang this script. Creating the
    artifact already succeeded before this runs; a failed launch here is
    reported, not escalated.
    """
    try:
        popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False


def _read_proc_version() -> str:
    try:
        return Path("/proc/version").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def main(
    argv: list[str],
    *,
    system: str,
    environ: dict,
    proc_version: str,
    which,
    popen,
    stdout,
    stderr,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args(argv)

    path = Path(args.path).resolve()
    if not path.exists():
        print(f"Error: artifact not found at {path}", file=stderr)
        return 1

    env = detect_environment(system, environ, proc_version)
    cmd = opener_command(env, path, which)
    opened = try_open(cmd, popen=popen) if cmd else False

    print(f"Artifact: {path}", file=stdout)
    if opened:
        print(f"Opened with: {' '.join(cmd)}", file=stdout)
    else:
        print(f"No opener available for this environment ({env}); open the file above manually.", file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(
        main(
            sys.argv[1:],
            system=platform.system(),
            environ=os.environ,
            proc_version=_read_proc_version(),
            which=shutil.which,
            popen=subprocess.Popen,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    )
