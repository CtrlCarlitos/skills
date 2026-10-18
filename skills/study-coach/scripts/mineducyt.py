import urllib.request
from pathlib import Path

from scripts.sources import make_source

REGISTRY = {
    ("matematica", "2"): {
        "title": "Libro de texto 2.° grado, Tomo 2",
        "url": "https://www.mined.gob.sv/materiales/2026/MATEMATICA/2.%20Libros%20de%20texto/Libro%20de%20texto%202.%C2%B0%20grado_Tomo%202.pdf",
    },
    ("matematica", "3"): {
        "title": "Libro de texto 3.° grado",
        "url": "https://www.mined.gob.sv/materiales/2026/MATEMATICA/2.%20Libros%20de%20texto/Libro%20de%20texto%203.%C2%B0%20grado.pdf",
    },
}


def _default_download(url):
    return urllib.request.urlopen(url).read()


def fetch_mineducyt_source(subject, grade, cache_dir, download=_default_download):
    entry = REGISTRY.get((subject.lower(), grade))
    if entry is None:
        return None

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_file = cache_dir / f"{subject}-{grade}.pdf"
    if not cached_file.exists():
        cached_file.write_bytes(download(entry["url"]))

    return make_source(
        "mineducyt", entry["title"], entry["url"],
        cached_path=str(cached_file), subject=subject, grade=grade,
    )
