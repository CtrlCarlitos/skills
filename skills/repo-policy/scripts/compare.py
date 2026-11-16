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


def _is_count(value) -> bool:
    # bool is an int subclass; an on/off setting is not a count.
    return isinstance(value, int) and not isinstance(value, bool)


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
        # A policy audits only the keys it states ("omit what you don't want
        # audited"); an omitted key is not a gap with a target of None (#42).
        if setting.key not in target:
            continue
        current_value = current.get(setting.key)
        target_value = target.get(setting.key)
        reason = exceptions.get(setting.key)

        if current_value == target_value:
            action = "None"
        elif target_value is False and current_value is True:
            # A policy's false on an on/off setting means "not required", never
            # "turn it off": the skill does not propose removing a protection.
            action = "None (exceeds policy)"
        elif reason:
            action = "Exception"
        elif _is_count(current_value) and _is_count(target_value):
            action = "Raise count" if target_value > current_value else "Lower count"
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
