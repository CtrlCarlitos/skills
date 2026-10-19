import json
import unittest
from scripts.flashcard_page import render_flashcard_html
from scripts.flashcard_schema import make_deck, make_flashcard

class RenderFlashcardHtmlTests(unittest.TestCase):
    def test_embeds_the_deck_data_as_valid_json(self):
        card = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Sustantivo")
        deck = make_deck("deck1", "mateo", "lenguaje", "sustantivos", [card])

        html = render_flashcard_html(deck)
        marker = '<script type="application/json" id="deck-data">'
        start = html.index(marker) + len(marker)
        end = html.index("</script>", start)
        embedded = json.loads(html[start:end])

        self.assertEqual(embedded, deck)

    def test_renders_every_cards_prompt_and_answer_and_id(self):
        card = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Es un sustantivo.")
        deck = make_deck("deck1", "mateo", "lenguaje", "sustantivos", [card])

        html = render_flashcard_html(deck)

        self.assertIn("Perro", html)
        self.assertIn("Es un sustantivo.", html)
        self.assertIn('data-card-id="c1"', html)

    def test_escapes_html_special_characters_in_prompt_and_answer(self):
        card = make_flashcard("c1", "matematica", "fracciones", "1 < 2 & 2 > 1", "Es verdadero.")
        deck = make_deck("deck1", "mateo", "matematica", "fracciones", [card])

        html = render_flashcard_html(deck)
        rendered_markup = html[html.index("</script>") + len("</script>"):]

        self.assertNotIn("1 < 2 & 2 > 1", rendered_markup)
        self.assertIn("1 &lt; 2 &amp; 2 &gt; 1", rendered_markup)

    def test_a_literal_script_closing_tag_in_a_card_does_not_break_the_embedded_json_block(self):
        card = make_flashcard("c1", "lenguaje", "html", "What closes a <script> tag?", "</script>")
        deck = make_deck("deck1", "mateo", "lenguaje", "html", [card])

        html = render_flashcard_html(deck)
        marker = '<script type="application/json" id="deck-data">'
        start = html.index(marker) + len(marker)
        end = html.index("</script>", start)
        embedded = json.loads(html[start:end])

        self.assertEqual(embedded, deck)

    def test_defaults_to_spanish_labels(self):
        card = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Sustantivo")
        deck = make_deck("deck1", "mateo", "lenguaje", "sustantivos", [card])

        html = render_flashcard_html(deck)

        self.assertIn('lang="es"', html)
        self.assertIn("Descargar resultados", html)

    def test_can_render_in_english_when_requested(self):
        card = make_flashcard("c1", "lenguaje", "sustantivos", "Perro", "Sustantivo")
        deck = make_deck("deck1", "mateo", "lenguaje", "sustantivos", [card])

        html = render_flashcard_html(deck, language="en")

        self.assertIn('lang="en"', html)
        self.assertIn("Download results", html)
