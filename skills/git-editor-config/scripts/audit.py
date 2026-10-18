"""CLI entry point: `python3 -m scripts.audit <repo-root>`. Read-only --
reads the repo's existing .gitattributes/.editorconfig if present and its
tracked files, prints the Markdown gap report. Never writes anything;
applying a gap is always a separate, itemized scripts.apply call.
"""
import sys
from pathlib import Path

from scripts.editorconfig import build_editorconfig_gaps, parse_editorconfig
from scripts.gaps import build_exec_bit_gaps, build_gitattributes_gaps
from scripts.gitattributes import parse_gitattributes
from scripts.gitignore_audit import find_tracked_generated_files, find_unignored_generated_files
from scripts.report import render_markdown
from scripts.scan import scan_tracked_files


def main() -> None:
    repo_root = Path(sys.argv[1])

    gitattributes_path = repo_root / ".gitattributes"
    existing_rules = parse_gitattributes(gitattributes_path.read_text(encoding="utf-8")) if gitattributes_path.exists() else []

    editorconfig_path = repo_root / ".editorconfig"
    existing_sections = parse_editorconfig(editorconfig_path.read_text(encoding="utf-8")) if editorconfig_path.exists() else []

    files = scan_tracked_files(repo_root)

    gitattributes_gaps = build_gitattributes_gaps(files, existing_rules)
    exec_bit_gaps = build_exec_bit_gaps(files)
    editorconfig_gaps = build_editorconfig_gaps(files, existing_sections)
    gitignore_gaps = find_tracked_generated_files(files) + find_unignored_generated_files(repo_root)

    print(render_markdown(gitattributes_gaps, exec_bit_gaps, editorconfig_gaps, gitignore_gaps))


if __name__ == "__main__":
    main()
