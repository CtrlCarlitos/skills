import json
from pathlib import Path


def parse_flashcard_results_export(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "deck_id" not in data or "results" not in data:
        raise ValueError(f"{path} is not a flashcard results export (expected an object with 'deck_id' and 'results')")
    if not isinstance(data["results"], list) or not all(
        isinstance(entry, dict) and "card_id" in entry and entry.get("result") in ("correct", "incorrect")
        for entry in data["results"]
    ):
        raise ValueError(f"{path} has a malformed results list")
    return data
