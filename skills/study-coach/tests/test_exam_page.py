import json
import unittest
from scripts.exam_page import render_exam_html
from scripts.exam_schema import make_exam, make_question

class RenderExamHtmlTests(unittest.TestCase):
    def test_embeds_the_exam_data_as_valid_json(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam)
        marker = '<script type="application/json" id="exam-data">'
        start = html.index(marker) + len(marker)
        end = html.index("</script>", start)
        embedded = json.loads(html[start:end])

        self.assertEqual(embedded, exam)

    def test_renders_every_questions_prompt_and_id(self):
        q1 = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        q2 = make_question("q2", "open_response", "lenguaje", "redaccion", "Write a sentence about your day.")
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q1, q2])

        html = render_exam_html(exam)

        self.assertIn("Perro is a noun.", html)
        self.assertIn('data-question-id="q1"', html)
        self.assertIn("Write a sentence about your day.", html)
        self.assertIn('data-question-id="q2"', html)

    def test_escapes_html_special_characters_in_a_prompt(self):
        # The embedded #exam-data JSON blob legitimately carries the prompt
        # unescaped (it must round-trip to the exact original exam dict,
        # per test_embeds_the_exam_data_as_valid_json above) -- escaping is
        # a property of the *rendered question markup* that follows it,
        # never of that data blob, so this test checks only the markup.
        q = make_question("q1", "open_response", "matematica", "fracciones", "2 < 3 & 3 > 2, ___?")
        exam = make_exam("exam1", "mateo", "matematica", "fracciones", "3", [q])

        html = render_exam_html(exam)
        rendered_markup = html[html.index("</script>") + len("</script>"):]

        self.assertNotIn("2 < 3 & 3 > 2", rendered_markup)
        self.assertIn("2 &lt; 3 &amp; 3 &gt; 2", rendered_markup)

    def test_rejects_an_unknown_question_type_rather_than_rendering_nothing(self):
        exam = {
            "exam_id": "e", "child_id": "c", "subject": "s", "topic": "t", "grade": "1",
            "questions": [{
                "question_id": "q1", "type": "essay", "subject": "s", "topic": "t",
                "competency": None, "prompt": "p", "options": None, "correct_answer": None,
            }],
        }

        with self.assertRaises(ValueError):
            render_exam_html(exam)

    def test_rejects_a_mismatched_correct_answer_shape_even_for_a_raw_loaded_exam(self):
        # exam_page.render_exam_html is also called on exams loaded straight
        # from JSON (the audit_exam CLI), bypassing make_question's own
        # validation entirely -- so render_exam_html must re-check the shape
        # itself, not assume every caller went through make_question first.
        exam = {
            "exam_id": "e", "child_id": "c", "subject": "s", "topic": "t", "grade": "1",
            "questions": [{
                "question_id": "q1", "type": "fill_in_blank", "subject": "s", "topic": "t",
                "competency": None, "prompt": "p", "options": None, "correct_answer": "not-a-list",
            }],
        }

        with self.assertRaises(ValueError):
            render_exam_html(exam)

    def test_multiple_choice_options_render_as_index_based_values_not_raw_text(self):
        # A radio's value is always a string. If the option text itself were
        # used as the value, an int/non-string correct_answer could never
        # compare equal to what the page reads back. Rendering by index and
        # mapping back through the embedded exam JSON keeps the original
        # option's type intact end to end.
        q = make_question("q1", "multiple_choice", "matematica", "fracciones", "How many?", options=["1/2", "1/3"], correct_answer="1/2")
        exam = make_exam("exam1", "mateo", "matematica", "fracciones", "3", [q])

        html = render_exam_html(exam)

        self.assertIn('value="0"', html)
        self.assertIn('value="1"', html)

    def test_matching_selects_have_no_preselected_default_answer(self):
        q = make_question("q1", "matching", "lenguaje", "sinonimos", "Match the pairs.", correct_answer={"grande": "enorme", "feliz": "contento"})
        exam = make_exam("exam1", "mateo", "lenguaje", "sinonimos", "4", [q])

        html = render_exam_html(exam)

        self.assertIn("disabled", html)

    def test_a_literal_script_closing_tag_in_a_prompt_does_not_break_the_embedded_json_block(self):
        q = make_question("q1", "open_response", "lenguaje", "redaccion", "What does </script> mean in HTML?")
        exam = make_exam("exam1", "mateo", "lenguaje", "redaccion", "4", [q])

        html = render_exam_html(exam)
        marker = '<script type="application/json" id="exam-data">'
        start = html.index(marker) + len(marker)
        end = html.index("</script>", start)
        embedded = json.loads(html[start:end])

        self.assertEqual(embedded, exam)

    def test_defaults_to_spanish_labels_for_kid_facing_text(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam)

        self.assertIn('lang="es"', html)
        self.assertIn("Verdadero", html)
        self.assertIn("Falso", html)
        self.assertIn("Descargar resultados", html)

    def test_can_render_in_english_when_requested(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam, language="en")

        self.assertIn('lang="en"', html)
        self.assertIn("Download results", html)

    def test_practice_mode_has_no_download_mechanism_at_all(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam, mode="practice")

        self.assertNotIn("Blob", html)
        self.assertNotIn("downloadResults", html)
        self.assertIn("showResults", html)
        self.assertIn('id="practice-results"', html)

    def test_exam_mode_is_unaffected_by_the_new_parameter(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam)

        self.assertIn("Blob", html)
        self.assertIn("downloadResults", html)

    def test_rejects_an_unknown_mode(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        with self.assertRaises(ValueError):
            render_exam_html(exam, mode="rehearsal")

    def test_practice_mode_shows_a_visible_practice_banner(self):
        # The spec's panic-vs-fluency framing depends on the kid being able
        # to tell a practice attempt apart from the real exam -- a missing
        # label would make a rehearsal look identical to the thing that
        # actually counts.
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam, mode="practice")

        self.assertIn("Práctica", html)

    def test_practice_mode_banner_in_english(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam, mode="practice", language="en")

        self.assertIn("Practice", html)

    def test_exam_mode_shows_no_practice_banner(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        html = render_exam_html(exam)

        self.assertNotIn("Práctica", html)
