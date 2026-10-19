import json
import tempfile
import unittest
from pathlib import Path
from scripts.flashcard_history import compute_card_weakness, record_flashcard_session, select_cards_for_review
from scripts.flashcard_schema import make_flashcard
from scripts.workspace import child_dir, resolve_workspace

class RecordFlashcardSessionTests(unittest.TestCase):
    def test_creates_the_history_file_on_the_first_session(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")

            history_path = record_flashcard_session(mateo, "deck1", "lenguaje", "sustantivos", "2026-10-19", [
                {"card_id": "c1", "result": "correct"},
            ])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["deck_id"], "deck1")

    def test_reviewing_the_same_deck_twice_accumulates_both_sessions(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            record_flashcard_session(mateo, "deck1", "lenguaje", "sustantivos", "2026-10-19", [{"card_id": "c1", "result": "incorrect"}])

            history_path = record_flashcard_session(mateo, "deck1", "lenguaje", "sustantivos", "2026-10-26", [{"card_id": "c1", "result": "correct"}])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(history), 2)
            self.assertEqual([h["reviewed_at"] for h in history], ["2026-10-19", "2026-10-26"])

class ComputeCardWeaknessTests(unittest.TestCase):
    def test_counts_misses_per_card_across_every_session(self):
        history = [
            {"deck_id": "deck1", "results": [{"card_id": "c1", "result": "incorrect"}, {"card_id": "c2", "result": "correct"}]},
            {"deck_id": "deck1", "results": [{"card_id": "c1", "result": "incorrect"}]},
        ]

        weakness = compute_card_weakness(history)

        self.assertEqual(weakness, {"c1": 2})

class SelectCardsForReviewTests(unittest.TestCase):
    def test_a_card_missed_before_appears_twice_a_card_never_missed_appears_once(self):
        c1 = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Sustantivo")
        c2 = make_flashcard("c2", "lenguaje", "sustantivos", "Correr", "Verbo")
        history = [{"deck_id": "deck1", "results": [{"card_id": "c1", "result": "incorrect"}]}]

        deck = select_cards_for_review([c1, c2], history)

        self.assertEqual(deck.count(c1), 2)
        self.assertEqual(deck.count(c2), 1)

    def test_no_history_at_all_returns_the_original_cards_unchanged(self):
        c1 = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Sustantivo")
        c2 = make_flashcard("c2", "lenguaje", "sustantivos", "Correr", "Verbo")

        deck = select_cards_for_review([c1, c2], [])

        self.assertEqual(deck, [c1, c2])
