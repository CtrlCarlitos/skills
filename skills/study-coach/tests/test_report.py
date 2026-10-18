import unittest
from scripts.report import aggregate_topic_results, classify_topic_strength, gap_report

class AggregateTopicResultsTests(unittest.TestCase):
    def test_aggregates_by_subject_and_topic_across_multiple_questions(self):
        results = [
            {"question_id": "q1", "subject": "lenguaje", "topic": "sustantivos", "correct": True},
            {"question_id": "q2", "subject": "lenguaje", "topic": "sustantivos", "correct": False},
            {"question_id": "q3", "subject": "matematica", "topic": "fracciones", "correct": True},
        ]

        aggregated = aggregate_topic_results(results)

        self.assertEqual(aggregated["lenguaje/sustantivos"], {"subject": "lenguaje", "topic": "sustantivos", "correct": 1, "total": 2})
        self.assertEqual(aggregated["matematica/fracciones"], {"subject": "matematica", "topic": "fracciones", "correct": 1, "total": 1})

    def test_an_unreviewed_open_response_question_counts_toward_total_but_not_correct(self):
        results = [{"question_id": "q1", "subject": "lenguaje", "topic": "redaccion", "correct": None}]

        aggregated = aggregate_topic_results(results)

        self.assertEqual(aggregated["lenguaje/redaccion"], {"subject": "lenguaje", "topic": "redaccion", "correct": 0, "total": 1})

class ClassifyTopicStrengthTests(unittest.TestCase):
    def test_too_few_questions_is_insufficient_data_regardless_of_score(self):
        self.assertEqual(classify_topic_strength(1, 1), "insufficient_data")

    def test_a_low_ratio_with_enough_questions_needs_work(self):
        self.assertEqual(classify_topic_strength(1, 3), "needs_work")

    def test_a_high_ratio_with_enough_questions_is_solid(self):
        self.assertEqual(classify_topic_strength(3, 3), "solid")

class GapReportTests(unittest.TestCase):
    def test_sorts_weakest_topics_first_and_puts_insufficient_data_last(self):
        aggregated = {
            "a/x": {"subject": "a", "topic": "x", "correct": 3, "total": 3},
            "b/y": {"subject": "b", "topic": "y", "correct": 0, "total": 3},
            "c/z": {"subject": "c", "topic": "z", "correct": 1, "total": 1},
        }

        report = gap_report(aggregated)

        self.assertEqual([r["topic"] for r in report], ["y", "x", "z"])
        self.assertEqual(report[0]["strength"], "needs_work")
        self.assertEqual(report[2]["strength"], "insufficient_data")
