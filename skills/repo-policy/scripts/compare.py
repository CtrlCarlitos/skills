"""Pure comparison engine: current repo state vs. a target policy.

No GitHub/filesystem access here -- inspect.py gathers `current`, policy.py
loads `target`; this module only diffs the two dicts it's handed.
"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Setting:
    key: str
    label: str
    action_when_mismatched: str
    format: Callable[[Any], str] = field(default=str)


def build_matrix(
    current: dict,
    target: dict,
    settings: list[Setting],
    exceptions: dict[str, str] | None = None,
) -> list[dict]:
    """One row per setting: label, current/target display values, the action
    to take, and the exception reason if the gap is a documented exception
    rather than something to fix.

    A documented exception (issue #5: "repository-specific CI checks and
    justified exceptions must remain configurable") is reported as its own
    distinct action, "Exception", never silently hidden and never reported
    as a plain unresolved gap.
    """
    exceptions = exceptions or {}
    rows = []
    for setting in settings:
        current_value = current.get(setting.key)
        target_value = target.get(setting.key)
        reason = exceptions.get(setting.key)

        if current_value == target_value:
            action = "None"
        elif reason:
            action = "Exception"
        else:
            action = setting.action_when_mismatched

        rows.append({
            "label": setting.label,
            "current": setting.format(current_value),
            "target": setting.format(target_value),
            "action": action,
            "exception_reason": reason,
        })
    return rows
