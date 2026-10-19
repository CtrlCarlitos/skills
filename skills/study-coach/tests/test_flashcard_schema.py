import unittest
from scripts.flashcard_schema import make_deck, make_flashcard

class MakeFlashcardTests(unittest.TestCase):
    def test_builds_a_flashcard_record_with_all_fields(self):
        card = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Es un sustantivo.", competency="identificar-sustantivos")

        self.assertEqual(card, {
            "card_id": "c1", "subject": "lenguaje", "topic": "sustantivos",
            "competency": "identificar-sustantivos", "prompt": "Perro", "answer": "Es un sustantivo.",
        })

class MakeDeckTests(unittest.TestCase):
    def test_builds_a_deck_record(self):
        card = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Es un sustantivo.")

        deck = make_deck("deck1", "mateo", "lenguaje", "sustantivos", [card])

        self.assertEqual(deck["deck_id"], "deck1")
        self.assertEqual(deck["cards"], [card])

    def test_rejects_a_deck_with_no_cards(self):
        with self.assertRaises(ValueError):
            make_deck("deck1", "mateo", "lenguaje", "sustantivos", [])
