"""Combines scan.py's raw facts with gitattributes.py's attribute
resolution and classify.py/exec_bit.py's per-file judgment into the two
gap-row lists the audit report is built from.

Coverage is attribute-name-aware, not a bare "does any pattern match"
check: a catchall like `* text=auto eol=lf` (this repo's own first
.gitattributes rule) matches every path, so a naive match-based check
would suppress every gap forever. Instead, each suggested attribute name
is checked individually against what's already resolved for that path --
a name already addressed by an existing rule (at any value) is treated as
covered, so only genuinely unaddressed attributes are ever reported. This
reproduces the real precedent this repo's own history needed (#9): a
`*.patch` rule had to be added on top of the `* text=auto eol=lf`
catchall specifically because that catchall addresses text/eol but says
nothing about diff.

A foundational disagreement about whether the path is text at all (the
suggestion says "text", an existing rule already says "-text", or vice
versa) suppresses the whole suggestion rather than a partial one -- that
is a real contradiction of an explicit human decision, never something to
partially override.
"""
from scripts.classify import classify_file
from scripts.exec_bit import exec_bit_drift
from scripts.gitattributes import resolve_attributes


def _attr_name(attr: str) -> str:
    if attr.startswith("-"):
        return attr[1:]
    return attr.split("=", 1)[0]


def _decompose(attrs: list[str]) -> list[tuple[str, object]]:
    decomposed = []
    for attr in attrs:
        if attr.startswith("-"):
            decomposed.append((attr[1:], False))
        elif "=" in attr:
            name, _, value = attr.partition("=")
            decomposed.append((name, value))
        else:
            decomposed.append((attr, True))
    return decomposed


def _missing_attrs(suggested_attrs: list[str], resolved: dict) -> list[str] | None:
    decomposed = _decompose(suggested_attrs)

    suggested_text = next((value for name, value in decomposed if name == "text"), None)
    resolved_text = resolved.get("text")
    if suggested_text is not None and resolved_text is not None:
        if bool(suggested_text) != bool(resolved_text):
            return None  # existing rule already decided text-vs-binary the other way

    missing_names = set()
    for name, _ in decomposed:
        if name == "eol" and resolved.get("text") is False:
            continue  # eol is moot on a path an existing rule already marks -text
        if name not in resolved:
            missing_names.add(name)

    if not missing_names:
        return None

    return [attr for attr in suggested_attrs if _attr_name(attr) in missing_names]


def build_gitattributes_gaps(files: list[dict], existing_rules: list[dict]) -> list[dict]:
    gaps = []
    for file in files:
        result = classify_file(file)
        if result is None:
            continue
        resolved = resolve_attributes(file["path"], existing_rules)
        missing_attrs = _missing_attrs(result["attrs"], resolved)
        if missing_attrs is None:
            continue
        gaps.append({
            "path": file["path"],
            "suggested_attrs": missing_attrs,
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
