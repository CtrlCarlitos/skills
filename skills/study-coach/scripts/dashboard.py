import html
import json
from pathlib import Path


def record_exam_report(child_dir, exam_id, subject, topic, taken_at, topic_reports):
    history_path = Path(child_dir) / "subjects" / subject / "exam_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    history.append({
        "exam_id": exam_id,
        "subject": subject,
        "topic": topic,
        "taken_at": taken_at,
        "topic_reports": topic_reports,
    })
    history_path.write_text(json.dumps(history), encoding="utf-8")

    return history_path


def render_dashboard_html(workspace):
    workspace = Path(workspace)
    children_dir = workspace / "children"

    sections = []
    for child_path in sorted(children_dir.iterdir()) if children_dir.is_dir() else []:
        if not child_path.is_dir():
            continue
        child_id = child_path.name
        rows = []
        subjects_dir = child_path / "subjects"
        for history_path in sorted(subjects_dir.glob("*/exam_history.json")) if subjects_dir.is_dir() else []:
            history = json.loads(history_path.read_text(encoding="utf-8"))
            for exam in reversed(history):
                for topic_report in exam["topic_reports"]:
                    rows.append(
                        f"<tr><td>{html.escape(exam['taken_at'])}</td>"
                        f"<td>{html.escape(topic_report['subject'])}/{html.escape(topic_report['topic'])}</td>"
                        f"<td>{topic_report['correct']}/{topic_report['total']}</td>"
                        f"<td>{html.escape(topic_report['strength'])}</td></tr>"
                    )
        rows_html = "".join(rows) if rows else "<tr><td colspan=\"4\">No exams yet.</td></tr>"
        sections.append(f"<h2>{html.escape(child_id)}</h2><table>{rows_html}</table>")

    body = "".join(sections) if sections else "<p>No children yet.</p>"
    result = f"<!doctype html>\n<html>\n<head><meta charset=\"utf-8\"><title>study-coach</title></head>\n<body>\n{body}\n</body>\n</html>"

    (workspace / "index.html").write_text(result, encoding="utf-8")
    return result
