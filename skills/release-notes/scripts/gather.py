#!/usr/bin/env python3
"""Gather the grounded, mechanical facts a release-notes draft needs: the
resolved range, the commits in it (with revert pairs collapsed and PR
references extracted), the repo-type guide to apply, and any existing
changelog file. Read-only -- writes nothing. Deciding which entry goes in
which section, and reading the diff of a refactor/chore/test commit for
hidden impact, is the agent's job once it has these facts, not this
script's.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.changelog_file import find_changelog, is_generated
from scripts.commits import collapse_reverted_pairs, extract_pr_reference, list_commits
from scripts.range import resolve_range
from scripts.repo_type import resolve_type_guide


def gather(
    repo_root: Path,
    base: str | None = None,
    head: str = "HEAD",
    type_name: str | None = None,
    home: Path | None = None,
    builtin_dir: Path | None = None,
    run=subprocess.run,
) -> dict:
    range_info = resolve_range(repo_root, base=base, head=head, run=run)
    commits = list_commits(repo_root, range_info["base"], range_info["head"], run=run)
    kept, not_included = collapse_reverted_pairs(commits)
    for commit in kept:
        commit["pr_reference"] = extract_pr_reference(commit)

    guide, guide_source = resolve_type_guide(
        repo_root,
        home if home is not None else Path.home(),
        builtin_dir if builtin_dir is not None else Path(__file__).resolve().parent.parent / "references",
        type_name=type_name,
    )

    changelog_path = find_changelog(repo_root)
    changelog_content = changelog_path.read_text(encoding="utf-8") if changelog_path else None

    return {
        "range": range_info,
        "commits": kept,
        "not_included": not_included,
        "repo_type": {"guide": guide, "source": guide_source},
        "changelog": {
            "path": str(changelog_path) if changelog_path else None,
            "generated": is_generated(changelog_content) if changelog_content else False,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root")
    parser.add_argument("--base", default=None, help="Defaults to the previous tag reachable from --head")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--type", dest="type_name", default=None, help="Defaults to auto-detection")
    args = parser.parse_args(argv)

    result = gather(Path(args.repo_root).resolve(), base=args.base, head=args.head, type_name=args.type_name)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
