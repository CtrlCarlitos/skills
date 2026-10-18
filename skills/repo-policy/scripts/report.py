"""Render a comparison matrix (from compare.build_matrix) as the Markdown
table shape issue #5 asks for: Setting / policy | Current | Target | Action.
"""


def _escape(value: str) -> str:
    return value.replace("|", r"\|")


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "| Setting / policy | Current | Target | Action |",
        "|---|---|---|---|",
    ]
    for row in rows:
        action = row["action"]
        if action == "Exception" and row.get("exception_reason"):
            action = f"Exception: {row['exception_reason']}"
        lines.append(
            f"| {_escape(row['label'])} | {_escape(row['current'])} | "
            f"{_escape(row['target'])} | {_escape(action)} |"
        )
    return "\n".join(lines)
