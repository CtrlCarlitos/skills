import shutil
from pathlib import Path

from scripts.sources import make_source


def _topic_dir(workspace, subject, topic):
    return Path(workspace) / "sources" / "santillana" / subject / topic


def record_santillana_photo(workspace, subject, topic, photo_path):
    photo_path = Path(photo_path)
    destination_dir = _topic_dir(workspace, subject, topic)
    destination_dir.mkdir(parents=True, exist_ok=True)

    existing = list(destination_dir.iterdir())
    destination = destination_dir / f"{len(existing) + 1:03d}{photo_path.suffix}"
    shutil.copyfile(photo_path, destination)

    return make_source(
        "santillana", destination.name, str(photo_path),
        cached_path=str(destination), subject=subject, topic=topic,
    )


def find_cached_santillana_sources(workspace, subject, topic):
    destination_dir = _topic_dir(workspace, subject, topic)
    if not destination_dir.is_dir():
        return []

    return [
        make_source("santillana", path.name, str(path), cached_path=str(path), subject=subject, topic=topic)
        for path in sorted(destination_dir.iterdir())
    ]
