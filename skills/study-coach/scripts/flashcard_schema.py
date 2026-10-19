def make_flashcard(card_id, subject, topic, prompt, answer, competency=None):
    return {
        "card_id": card_id,
        "subject": subject,
        "topic": topic,
        "competency": competency,
        "prompt": prompt,
        "answer": answer,
    }


def make_deck(deck_id, child_id, subject, topic, cards):
    if not cards:
        raise ValueError("a deck must have at least one card")

    return {
        "deck_id": deck_id,
        "child_id": child_id,
        "subject": subject,
        "topic": topic,
        "cards": cards,
    }
