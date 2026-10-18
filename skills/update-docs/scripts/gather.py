#!/usr/bin/env python3
"""Gather the grounded, mechanical facts an update-docs audit needs: the
repo-type guide, which docs are in scope (a diff/range's changed docs, or
the whole repo), the full set of tracked docs to search for stale
references elsewhere, which in-scope docs are machine-generated, and the
optional tool-check results (markdownlint, lychee, vale). Read-only --
writes nothing. Deciding whether a doc's claim is actually missing,
incorrect or stale against the code is the agent's job once it has these
facts, not this script's.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.diff_scope import changed_files
from scripts.doc_files import discover_doc_files, is_doc_path
from scripts.generated_docs import is_generated
from scripts.linkcheck import check_links
from scripts.markdownlint_check import check_markdown
from scripts.prose_check import ensure_builtin_vale_config, resolve_vale_config, check_prose
from scripts.repo_type import resolve_type_guide

_SKIPPED_CHECK = {"ran": False, "passed": True, "output": ""}

VALE_CACHE_DIR = Path.home() / ".cache" / "update-docs" / "vale-styles"
VALE_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "references" / "vale" / ".vale.ini"


def gather(
    repo_root: Path,
    scope: str = "diff",
    base: str | None = None,
    head: str = "HEAD",
    type_name: str | None = None,
    home: Path | None = None,
    builtin_types_dir: Path | None = None,
    vale_cache_dir: Path | None = None,
    vale_template_path: Path | None = None,
    markdownlint_config: str | None = None,
    lychee_config: str | None = None,
    run=subprocess.run,
    ensure_vale=ensure_builtin_vale_config,
) -> dict:
    if scope not in ("diff", "range", "repo"):
        raise ValueError(f"scope must be one of 'diff', 'range', 'repo', got {scope!r}")

    home = home if home is not None else Path.home()
    builtin_types_dir = (
        builtin_types_dir if builtin_types_dir is not None else Path(__file__).resolve().parent.parent / "references"
    )

    guide, guide_source = resolve_type_guide(repo_root, home, builtin_types_dir, type_name=type_name)
    all_doc_files = discover_doc_files(repo_root, run=run)

    result: dict = {
        "scope": scope,
        "repo_type": {"guide": guide, "source": guide_source},
        "all_doc_files": all_doc_files,
    }

    if scope == "repo":
        docs_in_scope = all_doc_files
    else:
        diff_base = base if scope == "range" else None
        changed = changed_files(repo_root, base=diff_base, head=head, run=run)
        result["changed_files"] = changed
        docs_in_scope = [p for p in changed if is_doc_path(p)]
        result["changed_doc_files"] = docs_in_scope

    result["docs_in_scope"] = docs_in_scope

    generated = []
    for rel_path in docs_in_scope:
        full_path = repo_root / rel_path
        if full_path.is_file() and is_generated(full_path.read_text(encoding="utf-8")):
            generated.append(rel_path)
    result["generated_docs"] = generated

    if not docs_in_scope:
        result["checks"] = {
            "markdownlint": dict(_SKIPPED_CHECK),
            "lychee": {**_SKIPPED_CHECK, "broken": []},
            "vale": {**_SKIPPED_CHECK, "findings": []},
        }
        return result

    abs_docs_in_scope = [str(repo_root / p) for p in docs_in_scope]

    result["checks"] = {
        "markdownlint": check_markdown(
            abs_docs_in_scope, config_path=markdownlint_config, cwd=str(repo_root), run=run
        ),
        "lychee": check_links(abs_docs_in_scope, config_path=lychee_config, cwd=str(repo_root), run=run),
        "vale": _run_vale_check(
            repo_root, abs_docs_in_scope,
            vale_cache_dir if vale_cache_dir is not None else VALE_CACHE_DIR,
            vale_template_path if vale_template_path is not None else VALE_TEMPLATE_PATH,
            run, ensure_vale,
        ),
    }
    return result


def _run_vale_check(repo_root, abs_docs_in_scope, cache_dir, template_path, run, ensure_vale) -> dict:
    synced_builtin_ini = ensure_vale(cache_dir, template_path, run=run)
    if synced_builtin_ini is not None:
        config_path = resolve_vale_config(repo_root, synced_builtin_ini)
    elif (repo_root / ".vale.ini").is_file():
        config_path = repo_root / ".vale.ini"
    else:
        return {**_SKIPPED_CHECK, "findings": []}

    return check_prose(abs_docs_in_scope, config_path=str(config_path), run=run)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root")
    parser.add_argument("--scope", choices=["diff", "range", "repo"], default="diff")
    parser.add_argument("--base", default=None)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--type", dest="type_name", default=None)
    args = parser.parse_args(argv)

    result = gather(
        Path(args.repo_root).resolve(), scope=args.scope, base=args.base, head=args.head, type_name=args.type_name
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
