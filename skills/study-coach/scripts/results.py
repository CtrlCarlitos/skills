import json
from pathlib import Path


def parse_results_export(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(entry, dict) and "question_id" in entry for entry in data):
        raise ValueError(f"{path} is not a JSON list of question result records")
    return data


def needs_review(results):
    return [entry["question_id"] for entry in results if entry["correct"] is None]


def apply_review_grades(results, grades):
    return [
        {**entry, "correct": grades[entry["question_id"]]} if entry["question_id"] in grades else dict(entry)
        for entry in results
    ]
