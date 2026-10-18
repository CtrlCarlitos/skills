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
        q = make_question("q1", "fill_in_blank", "matematica", "fracciones", "2 < 3 & 3 > 2, ___?")
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
