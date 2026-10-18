"""Itemized apply layer. Every function here acts on exactly the rows it's
given -- no function in this module iterates over anything other than its
`approved` argument, and there is no "apply everything" entry point
anywhere in this skill. See SKILL.md for why: a config file edit or a mode
bit change isn't reviewable the way a PR diff is, so approval has to be
itemized here instead.

Every append below works in binary-append mode and never reads+rewrites a
config file's existing bytes -- reading as text and writing it back (even
unchanged) would silently normalize CRLF line endings to LF, and joining a
new line onto one with no trailing newline would corrupt the last existing
rule. A path containing whitespace is quoted, matching gitattributes(5)/
gitignore(5)'s own C-style quoting -- an unquoted "my fix.patch" would
assign the attribute to a file literally named "my".
"""
import subprocess
from pathlib import Path


def _quote_if_needed(path: str) -> str:
    return f'"{path}"' if any(c.isspace() for c in path) else path


def _append_lines(path: Path, lines: list[str]) -> None:
    if not lines:
        return

    needs_leading_newline = path.exists() and path.stat().st_size > 0 and not path.read_bytes().endswith(b"\n")
    content = ("\n" if needs_leading_newline else "") + "".join(f"{line}\n" for line in lines)

    with path.open("ab") as f:
        f.write(content.encode("utf-8"))


def apply_gitattributes_rules(repo_root: Path, approved: list[dict]) -> None:
    lines = [f"{_quote_if_needed(row['path'])} {' '.join(row['suggested_attrs'])}" for row in approved]
    _append_lines(Path(repo_root) / ".gitattributes", lines)


def apply_exec_bit_fixes(repo_root: Path, approved: list[dict], run=subprocess.run) -> None:
    for row in approved:
        executable = row["drift"] == "missing"
        flag = "--chmod=+x" if executable else "--chmod=-x"
        run(["git", "update-index", flag, "--", row["path"]], cwd=repo_root, check=True, capture_output=True, text=True)

        # update-index only changes the index; the working-tree file's own
        # mode must agree too, or the next `git add -A`/`commit -a` on a
        # filemode=true checkout silently reverts this.
        target = Path(repo_root) / row["path"]
        current_mode = target.stat().st_mode
        if executable:
            target.chmod(current_mode | 0o111)
        else:
            target.chmod(current_mode & ~0o111)


def apply_editorconfig_sections(repo_root: Path, approved: list[dict], default_settings: dict) -> None:
    if not approved:
        return

    path = Path(repo_root) / ".editorconfig"
    lines = []
    for row in approved:
        lines.append(f"[*{row['extension']}]")
        lines.extend(f"{key} = {value}" for key, value in default_settings.items())
    section_block = "\n".join(lines) + "\n"

    if not path.exists():
        with path.open("wb") as f:
            f.write(("root = true\n\n" + section_block).encode("utf-8"))
        return

    existing = path.read_bytes()
    prefix = ("\n" if existing and not existing.endswith(b"\n") else "") + "\n"
    with path.open("ab") as f:
        f.write((prefix + section_block).encode("utf-8"))


def apply_gitignore_patterns(repo_root: Path, approved: list[dict]) -> None:
    lines = [_quote_if_needed(row["path"]) for row in approved]
    _append_lines(Path(repo_root) / ".gitignore", lines)
