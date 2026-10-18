"""The registry of policy settings this skill audits: how each one reads
from the normalized current-state dict, how it's labeled in the report,
and what action verb to show when it doesn't match the target policy.

This is the skill's actual policy surface -- issue #5's example matrix,
made concrete. Each row here is deliberately generic (no assumption about
any one repository); what counts as "the target" comes from policy.py.
"""
from scripts.compare import Setting


def merge_strategy_from_flags(flags: dict) -> str:
    """Normalize the three independent GitHub merge-method flags into the
    single enum a policy specifies (squash_only/merge_only/rebase_only/any/none).
    """
    allowed = [
        name
        for name, key in (
            ("squash", "allow_squash_merge"),
            ("merge", "allow_merge_commit"),
            ("rebase", "allow_rebase_merge"),
        )
        if flags.get(key)
    ]
    if len(allowed) == 1:
        return f"{allowed[0]}_only"
    if not allowed:
        return "none"
    return "any"


def _present(value) -> str:
    if value == "N/A":
        return "N/A"
    return "Present" if value else "Missing"


SETTINGS: list[Setting] = [
    Setting(key="default_branch", label="Default branch", action_when_mismatched="Rename default branch"),
    Setting(key="merge_strategy", label="Merge strategy", action_when_mismatched="Restrict"),
    Setting(key="delete_branch_on_merge", label="Delete merged branches", action_when_mismatched="Enable"),
    Setting(key="require_pull_request", label="PR required", action_when_mismatched="Add rule"),
    Setting(
        key="required_status_checks",
        label="Required CI",
        action_when_mismatched="Update checks",
        format=lambda v: ", ".join(v) if v else "(none)",
    ),
    Setting(key="required_review_thread_resolution", label="Review threads resolved", action_when_mismatched="Enable"),
    Setting(key="required_signatures", label="Signed commits", action_when_mismatched="Enable"),
    Setting(key="required_linear_history", label="Linear history", action_when_mismatched="Enable"),
    Setting(key="block_force_push", label="Force push blocked", action_when_mismatched="Enable"),
    Setting(key="block_branch_deletion", label="Branch deletion blocked", action_when_mismatched="Enable"),
    Setting(key="release_tags_protected", label="Release tags protected", action_when_mismatched="Add tag rule"),
    Setting(key="codeowners", label="CODEOWNERS", action_when_mismatched="Create", format=_present),
    Setting(key="contributing", label="CONTRIBUTING.md", action_when_mismatched="Create", format=_present),
    Setting(key="security_md", label="SECURITY.md", action_when_mismatched="Create", format=_present),
    Setting(key="pr_template", label="PR template", action_when_mismatched="Create", format=_present),
    Setting(key="issue_templates", label="Issue templates", action_when_mismatched="Create", format=_present),
    Setting(key="dependabot", label="Dependabot", action_when_mismatched="Create", format=_present),
    Setting(key="agents_md", label="AGENTS.md", action_when_mismatched="Create", format=_present),
]
