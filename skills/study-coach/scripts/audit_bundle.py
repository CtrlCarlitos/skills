import json
import sys
from pathlib import Path

from scripts.bundle import render_topic_index_html, write_bundle_files
from scripts.exam_page import render_exam_html
from scripts.flashcard_page import render_flashcard_html
from scripts.workspace import child_dir, resolve_workspace


def main():
    args = sys.argv[1:]
    practice = "--practice" in args
    if practice:
        args.remove("--practice")
    workspace_path, child_id, exam_path, deck_path = args

    exam = json.loads(Path(exam_path).read_text(encoding="utf-8"))
    deck = json.loads(Path(deck_path).read_text(encoding="utf-8"))

    exam_html = render_exam_html(exam)
    flashcard_html = render_flashcard_html(deck)
    practice_html = render_exam_html(exam, mode="practice") if practice else None

    workspace = resolve_workspace(Path(workspace_path))
    child_path = child_dir(workspace, child_id)
    written = write_bundle_files(
        child_path, exam["subject"], exam["topic"],
        exam_html=exam_html, flashcard_html=flashcard_html, practice_html=practice_html,
    )
    render_topic_index_html(child_path, exam["subject"], exam["topic"], written)

    for key, path in written.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
