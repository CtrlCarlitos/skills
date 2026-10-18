"""Regression tests for scripts/run_loop.py's train/test result splitting.

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import unittest

from scripts.run_loop import split_results


class SplitResultsTests(unittest.TestCase):
    def test_splits_by_train_query_membership(self):
        all_results = {
            "results": [
                {"query": "train-a", "pass": True},
                {"query": "test-b", "pass": False},
            ]
        }

        train, test = split_results(all_results, train_queries_set={"train-a"})

        self.assertEqual([r["query"] for r in train["results"]], ["train-a"])
        self.assertEqual([r["query"] for r in test["results"]], ["test-b"])

    def test_empty_test_set_yields_none(self):
        all_results = {"results": [{"query": "train-a", "pass": True}]}

        train, test = split_results(all_results, train_queries_set={"train-a"})

        self.assertIsNone(test)

    def test_errored_query_does_not_count_as_failed(self):
        all_results = {
            "results": [
                {"query": "train-a", "pass": True},
                {"query": "train-b", "pass": None},  # errored: no successful run
            ]
        }

        train, _ = split_results(all_results, train_queries_set={"train-a", "train-b"})

        self.assertEqual(train["summary"], {"total": 2, "passed": 1, "failed": 0, "errored": 1})


if __name__ == "__main__":
    unittest.main()
