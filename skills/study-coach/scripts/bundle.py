import html
from pathlib import Path

_FILENAMES = {"exam": "exam.html", "flashcards": "flashcards.html", "practice": "practice.html"}


def topic_dir(child_dir, subject, topic):
    result = Path(child_dir) / "subjects" / subject / topic
    result.mkdir(parents=True, exist_ok=True)
    return result


def write_bundle_files(child_dir, subject, topic, exam_html=None, flashcard_html=None, practice_html=None):
    directory = topic_dir(child_dir, subject, topic)
    contents = {"exam": exam_html, "flashcards": flashcard_html, "practice": practice_html}

    written = {}
    for key, content in contents.items():
        if content is None:
            continue
        path = directory / _FILENAMES[key]
        path.write_text(content, encoding="utf-8")
        written[key] = path
    return written


def render_topic_index_html(child_dir, subject, topic, written):
    links_html = "".join(
        f'<li><a href="{_FILENAMES[key]}">{html.escape(_FILENAMES[key])}</a></li>'
        for key in written
    )
    result = (
        f"<!doctype html>\n<html>\n<head><meta charset=\"utf-8\"><title>"
        f"{html.escape(subject)}/{html.escape(topic)}</title></head>\n<body>\n"
        f"<h1>{html.escape(subject)}/{html.escape(topic)}</h1>\n<ul>{links_html}</ul>\n</body>\n</html>"
    )

    (topic_dir(child_dir, subject, topic) / "index.html").write_text(result, encoding="utf-8")
    return result
