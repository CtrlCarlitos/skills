import shutil
from pathlib import Path

from scripts.sources import make_source

_ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".pdf"}


def _topic_dir(workspace, subject, grade, topic):
    return Path(workspace) / "sources" / "santillana" / subject / str(grade) / topic


def _next_sequence_number(directory):
    highest = 0
    for existing in directory.iterdir():
        if existing.stem.isdigit():
            highest = max(highest, int(existing.stem))
    return highest + 1


def record_santillana_photo(workspace, subject, topic, grade, photo_path):
    photo_path = Path(photo_path)
    destination_dir = _topic_dir(workspace, subject, grade, topic)
    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / f"{_next_sequence_number(destination_dir):03d}{photo_path.suffix}"
    shutil.copyfile(photo_path, destination)

    return make_source(
        "santillana", destination.name, str(photo_path),
        cached_path=str(destination), subject=subject, topic=topic, grade=grade,
    )


def find_cached_santillana_sources(workspace, subject, topic, grade):
    destination_dir = _topic_dir(workspace, subject, grade, topic)
    if not destination_dir.is_dir():
        return []

    return [
        make_source("santillana", path.name, str(path), cached_path=str(path), subject=subject, topic=topic, grade=grade)
        for path in sorted(destination_dir.iterdir())
        if path.suffix.lower() in _ALLOWED_SUFFIXES
    ]
