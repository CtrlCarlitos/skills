"""Render one Keep-a-Changelog-style release section from a given
{section_name: [bullet, ...]} mapping. Which bullet belongs in which
section is the agent's call per SKILL.md -- this just lays the result out
in a fixed order and skips sections with nothing in them.
"""

STANDARD_SECTIONS = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")
SECTION_ORDER = ("Breaking changes",) + STANDARD_SECTIONS + ("Upgrade notes", "Not included")


def render_release_section(
    version: str,
    date: str,
    sections: dict[str, list[str]],
    range_text: str | None = None,
    commit_count: int | None = None,
    pr_count: int | None = None,
    audience: str | None = None,
) -> str:
    lines = [f"## [{version}] - {date}", ""]

    metadata_parts = []
    if range_text:
        range_part = f"Range: `{range_text}`"
        if commit_count is not None and pr_count is not None:
            range_part += f" ({commit_count} commits, {pr_count} PRs)"
        metadata_parts.append(range_part)
    if audience:
        metadata_parts.append(f"Audience: {audience}")
    if metadata_parts:
        lines.append(". ".join(metadata_parts) + ".")
        lines.append("")

    for name in SECTION_ORDER:
        bullets = sections.get(name)
        if not bullets:
            continue
        lines.append(f"### {name}")
        lines.append("")
        lines.extend(f"- {item}" for item in bullets)
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines) + "\n"
