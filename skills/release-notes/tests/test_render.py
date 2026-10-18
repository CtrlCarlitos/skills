"""Tests for rendering one Keep-a-Changelog-style release section. Deciding
which bullet goes in which section is the agent's job per SKILL.md; this
module only lays out a given {section_name: [bullets]} mapping into
Markdown, in a fixed section order, omitting empty sections.

Run from skills/release-notes/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.render import render_release_section


class RenderReleaseSectionTests(unittest.TestCase):
    def test_renders_the_heading_with_version_and_date(self):
        result = render_release_section("1.1.0", "2026-02-01", {"Added": ["A new thing"]})

        self.assertTrue(result.startswith("## [1.1.0] - 2026-02-01\n"))

    def test_renders_standard_sections_in_keep_a_changelog_order(self):
        sections = {
            "Security": ["Patched X"],
            "Added": ["A new thing"],
            "Fixed": ["Fixed Y"],
        }

        result = render_release_section("1.1.0", "2026-02-01", sections)

        added_at = result.index("### Added")
        fixed_at = result.index("### Fixed")
        security_at = result.index("### Security")
        self.assertLess(added_at, fixed_at)
        self.assertLess(fixed_at, security_at)

    def test_omits_sections_with_no_entries(self):
        result = render_release_section("1.1.0", "2026-02-01", {"Added": ["A new thing"]})

        self.assertNotIn("### Changed", result)
        self.assertNotIn("### Removed", result)
        self.assertNotIn("### Deprecated", result)
        self.assertNotIn("### Fixed", result)
        self.assertNotIn("### Security", result)

    def test_renders_bullets_under_their_section(self):
        result = render_release_section("1.1.0", "2026-02-01", {"Added": ["First", "Second"]})

        self.assertIn("- First\n- Second", result)

    def test_headings_and_lists_have_blank_lines_around_them(self):
        """markdownlint's MD022/MD032 require a blank line between a
        heading and the content before/after it, and around a list --
        confirmed by actually running markdownlint-cli2 against sample
        output."""
        sections = {"Added": ["First"], "Fixed": ["Second"]}

        result = render_release_section("1.1.0", "2026-02-01", sections)

        self.assertIn("### Added\n\n- First\n\n### Fixed\n\n- Second\n", result)

    def test_breaking_changes_renders_before_the_standard_sections(self):
        """Per the issue's default format: Breaking changes is "ours" but
        sits first, ahead of the six Keep a Changelog sections -- Upgrade
        notes and Not included are the other two "ours" sections and sit
        after."""
        sections = {
            "Added": ["A new thing"],
            "Upgrade notes": ["Run migrate"],
            "Breaking changes": ["Removed old flag"],
            "Not included": ["Deferred to next release"],
        }

        result = render_release_section("1.1.0", "2026-02-01", sections)

        breaking_at = result.index("### Breaking changes")
        added_at = result.index("### Added")
        upgrade_at = result.index("### Upgrade notes")
        not_included_at = result.index("### Not included")
        self.assertLess(breaking_at, added_at)
        self.assertLess(added_at, upgrade_at)
        self.assertLess(upgrade_at, not_included_at)

    def test_the_metadata_line_matches_the_issues_exact_shape(self):
        """"Range: `<base>..<head>` (<N> commits, <M> PRs). Audience: <...>."
        on a single line, immediately under the heading."""
        result = render_release_section(
            "1.1.0", "2026-02-01", {"Added": ["A new thing"]},
            range_text="v1.0.0..v1.1.0", commit_count=5, pr_count=2, audience="users",
        )

        self.assertIn("Range: `v1.0.0..v1.1.0` (5 commits, 2 PRs). Audience: users.", result)

    def test_the_metadata_line_omits_the_commit_pr_count_when_not_given(self):
        result = render_release_section(
            "1.1.0", "2026-02-01", {"Added": ["A new thing"]},
            range_text="v1.0.0..v1.1.0", audience="users",
        )

        self.assertIn("Range: `v1.0.0..v1.1.0`. Audience: users.", result)

    def test_omits_the_metadata_line_entirely_when_neither_is_given(self):
        result = render_release_section("1.1.0", "2026-02-01", {"Added": ["A new thing"]})

        self.assertNotIn("Range:", result)
        self.assertNotIn("Audience:", result)

    def test_result_ends_with_exactly_one_trailing_newline(self):
        result = render_release_section("1.1.0", "2026-02-01", {"Added": ["A new thing"]})

        self.assertTrue(result.endswith("\n"))
        self.assertFalse(result.endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()
