import json
import sys
from pathlib import Path

from scripts.dashboard import record_exam_report, render_dashboard_html
from scripts.exam_page import render_exam_html
from scripts.grading import score_exam
from scripts.report import aggregate_topic_results, gap_report
from scripts.results import apply_review_grades, needs_review, parse_results_export
from scripts.workspace import child_dir, resolve_workspace


def _render(args):
    exam = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    Path(args[1]).write_text(render_exam_html(exam), encoding="utf-8")


def _score(args):
    exam_path, results_path, workspace_path, child_id, taken_at = args[:5]
    grades_path = args[args.index("--grades") + 1] if "--grades" in args else None

    exam = json.loads(Path(exam_path).read_text(encoding="utf-8"))
    raw_results = parse_results_export(Path(results_path))

    # The page's own "correct" field is untrusted (it's a second,
    # independent implementation of grading.grade_answer running in the
    # browser) -- grading.py is the one place that decides whether an
    # answer is correct, so recompute from the raw given_answer values.
    answers = {entry["question_id"]: entry["given_answer"] for entry in raw_results}
    scored = score_exam(exam, answers)

    if grades_path:
        grades = json.loads(Path(grades_path).read_text(encoding="utf-8"))
        scored = apply_review_grades(scored, grades)

    ungraded = needs_review(scored)
    if ungraded:
        print(f"needs review: {', '.join(ungraded)}")

    aggregated = aggregate_topic_results(scored)
    report = gap_report(aggregated)
    for row in report:
        print(f"{row['subject']}/{row['topic']}: {row['correct']}/{row['total']} ({row['strength']})")

    workspace = resolve_workspace(Path(workspace_path))
    child_path = child_dir(workspace, child_id)
    record_exam_report(child_path, exam["exam_id"], exam["subject"], exam["topic"], taken_at, report)
    render_dashboard_html(workspace)


def main():
    subcommand, rest = sys.argv[1], sys.argv[2:]
    if subcommand == "render":
        _render(rest)
    elif subcommand == "score":
        _score(rest)
    else:
        raise SystemExit(f"unknown subcommand: {subcommand!r}")


if __name__ == "__main__":
    main()
