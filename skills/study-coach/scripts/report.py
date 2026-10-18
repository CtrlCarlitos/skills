def aggregate_topic_results(results):
    aggregated = {}
    for entry in results:
        key = f"{entry['subject']}/{entry['topic']}"
        bucket = aggregated.setdefault(key, {"subject": entry["subject"], "topic": entry["topic"], "correct": 0, "total": 0, "pending": 0})
        if entry["correct"] is None:
            bucket["pending"] += 1
            continue
        bucket["total"] += 1
        if entry["correct"] is True:
            bucket["correct"] += 1
    return aggregated


def classify_topic_strength(correct, total, min_questions=2):
    if total < min_questions:
        return "insufficient_data"
    if correct / total < 0.7:
        return "needs_work"
    return "solid"


def gap_report(aggregated):
    rows = []
    for entry in aggregated.values():
        strength = classify_topic_strength(entry["correct"], entry["total"])
        rows.append({**entry, "strength": strength})

    def sort_key(row):
        if row["strength"] == "insufficient_data":
            return (1, 0)
        return (0, row["correct"] / row["total"])

    rows.sort(key=sort_key)
    return rows
