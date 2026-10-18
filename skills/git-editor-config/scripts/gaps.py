"""Combines scan.py's raw facts with gitattributes.py's coverage check and
classify.py/exec_bit.py's per-file judgment into the two gap-row lists the
audit report is built from. Coverage is checked before classification is
ever consulted, so an existing, human-authored rule always wins even when
classify_file would have suggested something different.
"""
from scripts.classify import classify_file
from scripts.exec_bit import exec_bit_drift
from scripts.gitattributes import is_covered


def build_gitattributes_gaps(files: list[dict], existing_rules: list[dict]) -> list[dict]:
    gaps = []
    for file in files:
        if is_covered(file["path"], existing_rules):
            continue
        result = classify_file(file)
        if result is None:
            continue
        gaps.append({
            "path": file["path"],
            "suggested_attrs": result["attrs"],
            "reason": result["reason"],
        })
    return gaps


def build_exec_bit_gaps(files: list[dict]) -> list[dict]:
    gaps = []
    for file in files:
        drift = exec_bit_drift(file)
        if drift is None:
            continue
        gaps.append({"path": file["path"], "drift": drift})
    return gaps
