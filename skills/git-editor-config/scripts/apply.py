"""Itemized apply layer. Every function here acts on exactly the rows it's
given -- no function in this module iterates over anything other than its
`approved` argument, and there is no "apply everything" entry point
anywhere in this skill. See SKILL.md for why: a config file edit or a mode
bit change isn't reviewable the way a PR diff is, so approval has to be
itemized here instead.
"""
import subprocess
from pathlib import Path


def apply_gitattributes_rules(repo_root: Path, approved: list[dict]) -> None:
    path = Path(repo_root) / ".gitattributes"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = "".join(f"{row['path']} {' '.join(row['suggested_attrs'])}\n" for row in approved)
    path.write_text(existing + additions, encoding="utf-8")


def apply_exec_bit_fixes(repo_root: Path, approved: list[dict], run=subprocess.run) -> None:
    for row in approved:
        flag = "--chmod=+x" if row["drift"] == "missing" else "--chmod=-x"
        run(["git", "update-index", flag, row["path"]], cwd=repo_root, check=True, capture_output=True, text=True)


def apply_editorconfig_sections(repo_root: Path, approved: list[dict], default_settings: dict) -> None:
    path = Path(repo_root) / ".editorconfig"
    existing = path.read_text(encoding="utf-8") if path.exists() else "root = true\n"
    additions = ""
    for row in approved:
        additions += f"\n[*{row['extension']}]\n"
        for key, value in default_settings.items():
            additions += f"{key} = {value}\n"
    path.write_text(existing + additions, encoding="utf-8")


def apply_gitignore_patterns(repo_root: Path, approved: list[dict]) -> None:
    path = Path(repo_root) / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = "".join(f"{row['path']}\n" for row in approved)
    path.write_text(existing + additions, encoding="utf-8")
