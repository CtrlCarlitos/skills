#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes Claude to trigger (read the skill)
for a set of queries. Outputs results as JSON.
"""

import argparse
import json
import os
import select
import subprocess
import sys
import queue as _queue
import threading as _threading
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import parse_skill_md


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/.

    Mimics how Claude Code discovers its project root, so the command file
    we create ends up where claude -p will look for it.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def find_conflicting_installed_skill(project_root: Path, skill_name: str) -> Path | None:
    """Return the SKILL.md of a real, already-installed skill with this name, if any.

    The eval harness injects a temporary decoy command to test a candidate
    description (see run_single_query). If a real skill with the same name
    is also installed (project- or user-scoped), the model can trigger that
    unrelated, already-shipped copy instead, and the harness can't tell the
    two apart — silently measuring the wrong description. Checked eagerly so
    that contamination is reported, not swallowed into a clean-looking score.
    """
    for candidate in (
        project_root / ".claude" / "skills" / skill_name / "SKILL.md",
        Path.home() / ".claude" / "skills" / skill_name / "SKILL.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def pump_stdout_to_queue(out, q: "_queue.Queue") -> None:
    """Drain a subprocess stdout stream into a queue; None marks EOF.

    Used on Windows, where select.select() only accepts sockets, so the
    select()+os.read() loop used elsewhere can't poll a subprocess pipe.
    Runs in a background thread; the caller polls `q` with a timeout the
    same way select's timeout worked on other platforms.
    """
    while True:
        chunk = out.read1(8192) if hasattr(out, "read1") else out.read(8192)
        if not chunk:
            q.put(None)
            return
        q.put(chunk)


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Creates a command file in .claude/commands/ so it appears in Claude's
    available_skills list, then runs `claude -p` with the raw query.
    Uses --include-partial-messages to detect triggering early from
    stream events (content_block_start) rather than waiting for the
    full assistant message, which only arrives after tool execution.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"
    project_commands_dir = Path(project_root) / ".claude" / "commands"
    command_file = project_commands_dir / f"{clean_name}.md"

    try:
        project_commands_dir.mkdir(parents=True, exist_ok=True)
        # Use YAML block scalar to avoid breaking on quotes in description
        indented_desc = "\n  ".join(skill_description.split("\n"))
        command_content = (
            f"---\n"
            f"description: |\n"
            f"  {indented_desc}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"This skill handles: {skill_description}\n"
        )
        command_file.write_text(command_content, encoding="utf-8")

        cmd = [
            "claude",
            "-p", query,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        if model:
            cmd.extend(["--model", model])

        # Remove CLAUDECODE env var to allow nesting claude -p inside a
        # Claude Code session. The guard is for interactive terminal conflicts;
        # programmatic subprocess usage is safe.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
            env=env,
        )

        # Windows: select() only accepts sockets, so a reader thread pumps
        # stdout chunks into a queue; None marks EOF.
        _win_q = None
        if sys.platform == "win32":
            _win_q = _queue.Queue()
            _threading.Thread(
                target=pump_stdout_to_queue, args=(process.stdout, _win_q), daemon=True
            ).start()

        triggered = False
        start_time = time.time()
        buffer = ""
        # Track state for stream event detection
        pending_tool_name = None
        accumulated_json = ""

        try:
            while time.time() - start_time < timeout:
                if _win_q is not None:
                    try:
                        chunk = _win_q.get(timeout=1.0)
                    except _queue.Empty:
                        continue
                    if chunk is None:
                        break
                else:
                    if process.poll() is not None:
                        remaining = process.stdout.read()
                        if remaining:
                            buffer += remaining.decode("utf-8", errors="replace")
                        break

                    ready, _, _ = select.select([process.stdout], [], [], 1.0)
                    if not ready:
                        continue

                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        break
                buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Early detection via stream events
                    if event.get("type") == "stream_event":
                        se = event.get("event", {})
                        se_type = se.get("type", "")

                        if se_type == "content_block_start":
                            cb = se.get("content_block", {})
                            if cb.get("type") == "tool_use":
                                tool_name = cb.get("name", "")
                                if tool_name in ("Skill", "Read"):
                                    pending_tool_name = tool_name
                                    accumulated_json = ""
                                else:
                                    return False

                        elif se_type == "content_block_delta" and pending_tool_name:
                            delta = se.get("delta", {})
                            if delta.get("type") == "input_json_delta":
                                accumulated_json += delta.get("partial_json", "")
                                if clean_name in accumulated_json or f'"{skill_name}"' in accumulated_json:
                                    return True

                        elif se_type in ("content_block_stop", "message_stop"):
                            if pending_tool_name:
                                return clean_name in accumulated_json or f'"{skill_name}"' in accumulated_json
                            if se_type == "message_stop":
                                return False

                    # Fallback: full assistant message
                    elif event.get("type") == "assistant":
                        message = event.get("message", {})
                        for content_item in message.get("content", []):
                            if content_item.get("type") != "tool_use":
                                continue
                            tool_name = content_item.get("name", "")
                            tool_input = content_item.get("input", {})
                            if tool_name == "Skill" and (clean_name in tool_input.get("skill", "") or tool_input.get("skill", "") == skill_name):
                                triggered = True
                            elif tool_name == "Read" and clean_name in tool_input.get("file_path", ""):
                                triggered = True
                            return triggered

                    elif event.get("type") == "result":
                        return triggered
        finally:
            # Clean up process on any exit path (return, exception, timeout)
            if process.poll() is None:
                process.kill()
                process.wait()

        return triggered
    finally:
        if command_file.exists():
            command_file.unlink()


def summarize(results: list[dict]) -> dict:
    """Count passed/failed/errored over a list of per-query result dicts.

    A result's `pass` is True, False, or None (errored: no successful run,
    so it is neither a measured pass nor a measured fail).
    """
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["pass"] is True),
        "failed": sum(1 for r in results if r["pass"] is False),
        "errored": sum(1 for r in results if r["pass"] is None),
    }


def aggregate_results(
    eval_set: list[dict],
    query_outcomes: dict[str, list[bool | BaseException]],
    trigger_threshold: float = 0.5,
) -> dict:
    """Turn raw per-run outcomes into per-query stats and a summary.

    Each outcome is either a bool (a real trigger measurement) or an
    exception (the run itself failed: subprocess crash, missing `claude`
    CLI, timeout, etc.). Exceptions are never averaged in as non-triggers —
    a query with no successful runs is reported as errored, not failed, so
    a broken harness can't masquerade as a 0% skill score.
    """
    results = []
    for item in eval_set:
        query = item["query"]
        should_trigger = item["should_trigger"]
        outcomes = query_outcomes.get(query, [])
        triggers = [o for o in outcomes if isinstance(o, bool)]
        errors = [o for o in outcomes if not isinstance(o, bool)]

        entry = {
            "query": query,
            "should_trigger": should_trigger,
            "runs": len(outcomes),
            "errors": len(errors),
        }
        if triggers:
            trigger_rate = sum(triggers) / len(triggers)
            did_pass = (
                trigger_rate >= trigger_threshold
                if should_trigger
                else trigger_rate < trigger_threshold
            )
            entry.update({
                "trigger_rate": trigger_rate,
                "triggers": sum(triggers),
                "pass": did_pass,
            })
        else:
            entry.update({
                "trigger_rate": None,
                "triggers": 0,
                "pass": None,
                "error_messages": [str(e) for e in errors],
            })
        results.append(entry)

    return {
        "results": results,
        "summary": summarize(results),
    }


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    conflict = find_conflicting_installed_skill(project_root, skill_name)
    if conflict:
        print(
            f"WARNING: a real skill named '{skill_name}' is already installed at "
            f"{conflict}. The model may trigger that installed copy's actual "
            "description instead of the candidate description under test, and "
            "this harness cannot tell the two apart. Results below may measure "
            "the wrong description — uninstall or rename the installed copy "
            "before trusting this score.",
            file=sys.stderr,
        )

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_outcomes: dict[str, list[bool | BaseException]] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_outcomes.setdefault(query, [])
            try:
                query_outcomes[query].append(future.result())
            except Exception as e:
                print(f"Warning: query run failed (harness error, not a non-trigger): {e}", file=sys.stderr)
                query_outcomes[query].append(e)

    aggregated = aggregate_results(eval_set, query_outcomes, trigger_threshold)

    if aggregated["summary"]["errored"]:
        print(
            f"Warning: {aggregated['summary']['errored']} of "
            f"{aggregated['summary']['total']} queries had no successful run "
            "(harness errors) and are excluded from passed/failed counts.",
            file=sys.stderr,
        )

    return {
        "skill_name": skill_name,
        "description": description,
        "eval_validity_warning": (
            f"A real skill named '{skill_name}' is already installed at {conflict}; "
            "results may measure that installed copy instead of this candidate "
            "description."
            if conflict
            else None
        ),
        **aggregated,
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for claude -p (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    parser.add_argument("--project-root", default=None, help="Repo to run claude -p in (default: nearest .claude/ above cwd)")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = Path(args.project_root).resolve() if args.project_root else find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
