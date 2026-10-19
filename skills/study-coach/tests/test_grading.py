import unittest
from scripts.exam_schema import make_exam, make_question
from scripts.grading import grade_answer, is_self_gradable, score_exam

class IsSelfGradableTests(unittest.TestCase):
    def test_open_response_is_not_self_gradable(self):
        q = make_question("q1", "open_response", "lenguaje", "redaccion", "Write a sentence.")
        self.assertFalse(is_self_gradable(q))

    def test_every_other_type_is_self_gradable(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        self.assertTrue(is_self_gradable(q))

class GradeAnswerTests(unittest.TestCase):
    def test_open_response_always_returns_none(self):
        q = make_question("q1", "open_response", "lenguaje", "redaccion", "Write a sentence.")
        self.assertIsNone(grade_answer(q, "Mi perro es grande."))

    def test_fill_in_blank_normalizes_case_and_whitespace(self):
        q = make_question("q1", "fill_in_blank", "matematica", "fracciones", "1/2 + 1/2 = ___", correct_answer=["uno", "1"])
        self.assertTrue(grade_answer(q, "  UNO  "))
        self.assertFalse(grade_answer(q, "dos"))

    def test_matching_requires_an_exact_pair_mapping(self):
        q = make_question("q1", "matching", "lenguaje", "sinonimos", "Match the pairs.", correct_answer={"grande": "enorme", "feliz": "contento"})
        self.assertTrue(grade_answer(q, {"grande": "enorme", "feliz": "contento"}))
        self.assertFalse(grade_answer(q, {"grande": "enorme", "feliz": "triste"}))

    def test_multiple_choice_compares_exactly(self):
        q = make_question("q1", "multiple_choice", "matematica", "fracciones", "Which is bigger?", options=["1/2", "1/3"], correct_answer="1/2")
        self.assertTrue(grade_answer(q, "1/2"))
        self.assertFalse(grade_answer(q, "1/3"))

class ScoreExamTests(unittest.TestCase):
    def test_scores_every_question_and_carries_its_tags(self):
        q1 = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        q2 = make_question("q2", "open_response", "lenguaje", "redaccion", "Write a sentence.")
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q1, q2])

        results = score_exam(exam, {"q1": True, "q2": "Mi perro es grande."})

        self.assertEqual(results[0], {
            "question_id": "q1", "subject": "lenguaje", "topic": "sustantivos", "competency": None,
            "type": "true_false", "given_answer": True, "correct": True,
        })
        self.assertIsNone(results[1]["correct"])
        self.assertEqual(results[1]["given_answer"], "Mi perro es grande.")

    def test_an_unanswered_question_grades_as_incorrect_not_skipped(self):
        q = make_question("q1", "true_false", "lenguaje", "sustantivos", "Perro is a noun.", correct_answer=True)
        exam = make_exam("exam1", "mateo", "lenguaje", "sustantivos", "4", [q])

        results = score_exam(exam, {})

        self.assertIsNone(results[0]["given_answer"])
        self.assertFalse(results[0]["correct"])
