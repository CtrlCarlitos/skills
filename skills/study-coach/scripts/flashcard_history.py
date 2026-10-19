import json
from pathlib import Path


def record_flashcard_session(child_dir, deck_id, subject, topic, reviewed_at, results):
    history_path = Path(child_dir) / "subjects" / subject / "flashcard_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    # Unlike dashboard.record_exam_report, this always appends: reviewing
    # the same deck_id on two different days is two genuinely separate
    # sessions, not a correction to one, so there is no replace-by-id step.
    history.append({
        "deck_id": deck_id,
        "subject": subject,
        "topic": topic,
        "reviewed_at": reviewed_at,
        "results": results,
    })
    history_path.write_text(json.dumps(history), encoding="utf-8")

    return history_path


def compute_card_weakness(history):
    weakness = {}
    for entry in history:
        for result in entry["results"]:
            if result["result"] == "incorrect":
                weakness[result["card_id"]] = weakness.get(result["card_id"], 0) + 1
    return weakness


def select_cards_for_review(cards, history, max_extra_appearances=1):
    weakness = compute_card_weakness(history)
    selected = []
    for card in cards:
        selected.append(card)
        misses = weakness.get(card["card_id"], 0)
        extra = min(misses, max_extra_appearances)
        selected.extend([card] * extra)
    return selected
