"""Turn an evals/evals.json scenario's `ops` list into a real git repo, so
the fixtures described there are actually executable against the real
range/commits/repo_type modules, not just descriptive text.

Each op is one of:
  {"commit": "<message>", "files": {"<relative path>": "<content>", ...}}
  {"tag": "<name>"}
  {"revert": "<ref>"}
"""
import subprocess
from pathlib import Path


def _run(args: list[str], cwd: Path, run) -> None:
    run(args, cwd=cwd, check=True, capture_output=True, text=True)


def build_fixture(ops: list[dict], root: Path, run=subprocess.run) -> None:
    _run(["git", "init", "-q", "-b", "main"], root, run)
    _run(["git", "config", "user.email", "x@x.com"], root, run)
    _run(["git", "config", "user.name", "x"], root, run)

    for op in ops:
        if "commit" in op:
            for path, content in op.get("files", {}).items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            _run(["git", "add", "-A"], root, run)
            _run(["git", "commit", "-q", "-m", op["commit"]], root, run)
        elif "tag" in op:
            _run(["git", "tag", op["tag"]], root, run)
        elif "revert" in op:
            _run(["git", "revert", "--no-edit", op["revert"]], root, run)
        else:
            raise ValueError(f"Unknown fixture op: {op!r}")
