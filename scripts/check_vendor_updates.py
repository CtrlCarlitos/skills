#!/usr/bin/env python3
"""Report vendored subtrees whose pinned upstream content is no longer current."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from urllib import error, parse, request


API_ROOT = "https://api.github.com"
EXPECTED_KEYS = {"repo", "path", "commit", "date"}
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class CheckerError(RuntimeError):
    """A metadata or GitHub API failure that must not look like no drift."""


@dataclass(frozen=True)
class Upstream:
    repo: str
    path: str
    commit: str
    date: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    pinned_sha: str
    current_sha: str
    default_branch: str


def parse_upstream(path: Path) -> Upstream:
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CheckerError(f"cannot read {path}: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if "=" not in line:
            raise CheckerError(f"{path}:{line_number}: expected key=value")
        key, value = line.split("=", 1)
        if key not in EXPECTED_KEYS:
            raise CheckerError(f"{path}:{line_number}: unknown key {key!r}")
        if key in fields:
            raise CheckerError(f"{path}:{line_number}: duplicate key {key!r}")
        if not value:
            raise CheckerError(f"{path}:{line_number}: empty value for {key!r}")
        fields[key] = value

    missing = EXPECTED_KEYS - fields.keys()
    if missing:
        raise CheckerError(f"{path}: missing keys: {', '.join(sorted(missing))}")
    if not COMMIT_RE.fullmatch(fields["commit"]):
        raise CheckerError(f"{path}: commit must be 40 lowercase hexadecimal characters")
    return Upstream(**fields)


def github_json(url: str, token: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "CtrlCarlitos-skills-vendor-update-check",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api_request = request.Request(url, headers=headers)
    try:
        with request.urlopen(api_request, timeout=30) as response:
            payload = json.load(response)
    except (
        error.HTTPError,
        error.URLError,
        TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise CheckerError(f"GitHub API request failed for {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CheckerError(f"GitHub API returned a non-object for {url}")
    return payload


def _required_string(payload: dict, field: str, url: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise CheckerError(f"GitHub API response for {url} lacks a non-empty {field!r}")
    return value


def _commit_tree_sha(payload: dict, url: str) -> str:
    commit = payload.get("commit")
    tree = commit.get("tree") if isinstance(commit, dict) else None
    if not isinstance(tree, dict):
        raise CheckerError(f"GitHub API response for {url} lacks commit.tree")
    return _required_string(tree, "sha", url)


def _path_tree_sha(
    repo_url: str,
    ref: str,
    path: str,
    token: str,
    fetch,
) -> str:
    commit_url = f"{repo_url}/commits/{parse.quote(ref, safe='')}"
    tree_sha = _commit_tree_sha(fetch(commit_url, token), commit_url)

    for segment in path.split("/"):
        tree_url = f"{repo_url}/git/trees/{tree_sha}"
        payload = fetch(tree_url, token)
        entries = payload.get("tree")
        if not isinstance(entries, list):
            raise CheckerError(f"GitHub API response for {tree_url} lacks a tree list")
        matches = [
            entry
            for entry in entries
            if isinstance(entry, dict) and entry.get("path") == segment
        ]
        if len(matches) != 1 or matches[0].get("type") != "tree":
            raise CheckerError(f"{path!r} is not a directory at {ref}")
        tree_sha = _required_string(matches[0], "sha", tree_url)
    return tree_sha


def check_vendor(
    name: str,
    vendor_root: Path,
    token: str,
    fetch=github_json,
) -> CheckResult:
    upstream = parse_upstream(vendor_root / name / "UPSTREAM")
    repo_component = parse.quote(upstream.repo, safe="/")
    repo_url = f"{API_ROOT}/repos/{repo_component}"
    default_branch = _required_string(
        fetch(repo_url, token), "default_branch", repo_url
    )

    return CheckResult(
        name=name,
        pinned_sha=_path_tree_sha(
            repo_url, upstream.commit, upstream.path, token, fetch
        ),
        current_sha=_path_tree_sha(
            repo_url, default_branch, upstream.path, token, fetch
        ),
        default_branch=default_branch,
    )


def _write_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("## Vendored upstream check\n\n")
            summary.write("\n".join(f"- {line}" for line in lines))
            summary.write("\n")
    except OSError as exc:
        raise CheckerError(f"cannot write GITHUB_STEP_SUMMARY: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vendors", nargs="*", help="vendor names to check")
    parser.add_argument(
        "--vendor-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "vendor",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GH_TOKEN or GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    names = args.vendors or sorted(
        path.parent.name for path in args.vendor_root.glob("*/UPSTREAM")
    )
    if not names:
        print(f"ERROR: no UPSTREAM files found under {args.vendor_root}", file=sys.stderr)
        return 2

    lines: list[str] = []
    stale = False
    failed = False
    for name in names:
        try:
            result = check_vendor(name, args.vendor_root, token)
        except CheckerError as exc:
            line = f"ERROR {name}: {exc}"
            failed = True
        else:
            if result.pinned_sha == result.current_sha:
                line = f"PASS {name}: unchanged on {result.default_branch}"
            else:
                line = (
                    f"STALE {name}: pinned {result.pinned_sha[:12]}, "
                    f"{result.default_branch} {result.current_sha[:12]}"
                )
                stale = True
        lines.append(line)
        print(line)

    try:
        _write_summary(lines)
    except CheckerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if failed:
        return 2
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
