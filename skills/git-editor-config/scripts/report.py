"""Renders the four gap-row lists gaps.py/editorconfig.py/gitignore_audit.py
produce as Markdown tables, repo-policy/scripts/report.py's exact table
convention (header row, separator, one row per item, pipe-escaped cells).
A section with no rows is omitted entirely, never printed as an empty table.
"""


def _escape(value) -> str:
    text = " ".join(value) if isinstance(value, list) else str(value)
    return text.replace("|", r"\|")


def _render_table(columns: list[tuple[str, str]], rows: list[dict]) -> str:
    headers = [label for label, _ in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in rows:
        cells = [_escape(row[key]) for _, key in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_markdown(
    gitattributes_gaps: list[dict],
    exec_bit_gaps: list[dict],
    editorconfig_gaps: list[dict],
    gitignore_gaps: list[dict],
) -> str:
    sections = [
        (".gitattributes gaps", gitattributes_gaps, [("Path", "path"), ("Suggested", "suggested_attrs"), ("Reason", "reason")]),
        ("Executable-bit drift", exec_bit_gaps, [("Path", "path"), ("Drift", "drift")]),
        (".editorconfig gaps", editorconfig_gaps, [("Extension", "extension"), ("Example", "example_path")]),
        (".gitignore gaps", gitignore_gaps, [("Path", "path"), ("Reason", "reason")]),
    ]

    rendered = []
    for title, rows, columns in sections:
        if not rows:
            continue
        rendered.append(f"## {title}\n\n" + _render_table(columns, rows))

    if not rendered:
        return "No gaps found."

    return "\n\n".join(rendered)
