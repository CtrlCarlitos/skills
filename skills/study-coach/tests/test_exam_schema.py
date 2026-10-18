import unittest
from scripts.exam_schema import make_exam, make_question

class MakeQuestionTests(unittest.TestCase):
    def test_builds_a_question_record_with_all_fields(self):
        q = make_question(
            "q1", "multiple_choice", "matematica", "fracciones", "Which is bigger?",
            options=["1/2", "1/3"], correct_answer="1/2", competency="comparar-fracciones",
        )
        self.assertEqual(q, {
            "question_id": "q1", "type": "multiple_choice", "subject": "matematica", "topic": "fracciones",
            "competency": "comparar-fracciones", "prompt": "Which is bigger?",
            "options": ["1/2", "1/3"], "correct_answer": "1/2",
        })

    def test_rejects_an_unknown_question_type(self):
        with self.assertRaises(ValueError):
            make_question("q1", "essay", "matematica", "fracciones", "Explain.")

class MakeExamTests(unittest.TestCase):
    def test_builds_an_exam_record(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)

        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        self.assertEqual(exam["exam_id"], "exam1")
        self.assertEqual(exam["questions"], [q])

    def test_rejects_an_exam_with_no_questions(self):
        with self.assertRaises(ValueError):
            make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [])
