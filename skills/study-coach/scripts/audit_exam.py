import json
import sys
from pathlib import Path

from scripts.dashboard import record_exam_report, render_dashboard_html
from scripts.exam_page import render_exam_html
from scripts.report import aggregate_topic_results, gap_report
from scripts.results import needs_review, parse_results_export
from scripts.workspace import child_dir, resolve_workspace


def _render(args):
    exam = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    Path(args[1]).write_text(render_exam_html(exam), encoding="utf-8")


def _tag_results_with_exam_metadata(exam, results):
    questions_by_id = {q["question_id"]: q for q in exam["questions"]}
    return [
        {**result, "subject": questions_by_id[result["question_id"]]["subject"], "topic": questions_by_id[result["question_id"]]["topic"]}
        for result in results
    ]


def _score(args):
    exam_path, results_path, workspace_path, child_id, taken_at = args
    exam = json.loads(Path(exam_path).read_text(encoding="utf-8"))
    results = parse_results_export(Path(results_path))

    ungraded = needs_review(results)
    if ungraded:
        print(f"needs review: {', '.join(ungraded)}")

    tagged_results = _tag_results_with_exam_metadata(exam, results)
    aggregated = aggregate_topic_results(tagged_results)
    report = gap_report(aggregated)
    for row in report:
        print(f"{row['subject']}/{row['topic']}: {row['correct']}/{row['total']} ({row['strength']})")

    workspace = resolve_workspace(Path(workspace_path))
    mateo = child_dir(workspace, child_id)
    record_exam_report(mateo, exam["exam_id"], exam["subject"], exam["topic"], taken_at, report)
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
