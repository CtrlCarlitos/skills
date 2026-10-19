# study-coach: Exam Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `study-coach` skill's exam engine: a question/exam schema, per-type client-side self-grading (with open/free-response correctly left ungraded, never guessed), a self-contained static exam HTML page, the results-export-and-reingest round trip, a topic-tagged gap report, and the per-child, accumulating dashboard (`index.html`) the design doc's longitudinal view requires.

**Architecture:** `exam_schema.py` defines the question/exam record shapes every other module reads and writes. `grading.py` is the only place that decides whether a given answer is correct, per type -- the rest of the pipeline treats its output as ground truth. `exam_page.py` renders a self-contained HTML page from an exam record (no network, no backend). `results.py` parses a downloaded results-export file and merges in a human/Claude review grade for ungraded open-response items. `report.py` aggregates per-topic strength from scored results. `dashboard.py` persists each exam's report into the child's own history (never overwriting a prior exam) and renders the family's `index.html`. This plan's code never writes the actual question content (prompts/options/correct answers) -- that's the orchestrating skill's job (Plan 3), already grounded via Plan 1's `ground_topic`; this plan validates, renders, grades, aggregates, and persists whatever it's handed.

**Tech Stack:** Python 3 stdlib only (continuing Plan 1's constraint: no new third-party dependency, no `requirements.txt`). No network calls anywhere in this plan.

**Spec:** `docs/superpowers/specs/2026-10-18-study-coach-design.md` (this is Plan 2 of 3 for the spec's "study-coach v1"; flashcards and the two parent-facing entry points follow in Plan 3, and the video pipeline is deferred to its own later issue). Builds on Plan 1 (`docs/superpowers/plans/2026-10-18-study-coach-workspace-grounding.md`), merged as PR #32: this plan consumes `scripts/workspace.py`'s `child_dir` and nothing else from it.

## Global Constraints

- **Question types, verbatim from the spec's Decided section:** multiple choice, single-select (radio), fill-in-the-blank, open/free response, plus true/false and matching.
- **Grading split, verbatim from the spec:** multiple choice, single-select, true/false, matching, and fill-in-the-blank (exact or close-match text) all grade themselves client-side. Open/free-response cannot self-grade -- there's no backend to evaluate free text against; these fold into the already-settled "parent brings results back to the next invocation" flow.
- **Topic tagging, verbatim from the spec:** every question is tagged to the specific competency/topic it tests regardless of type, so results aggregate into a per-topic breakdown -- the thing the user asked for by name -- not a single score.
- **No backend, despite producing the exam:** a static exam page cannot write back to the workspace. It produces a downloadable results export; the parent brings that file back into the next `study-coach` invocation, which is where the persisted report and dashboard actually update.
- **Longitudinal dashboard, verbatim from the spec's Goals:** a single `index.html` front door shows a running, longitudinal view of how each subject/topic is tracking across exams over time -- not just the latest exam in isolation.
- **Multi-child, continuing Plan 1:** every function here that touches the workspace operates on one child's own partition (`child_dir`'s return value); nothing pools two children's history together.

## Review Focus

- **An open/free-response question, at every stage of the pipeline** -- `grade_answer` must return `None` (not `True`/`False`), `score_exam` must carry that `None` through, and `aggregate_topic_results` must count it toward `total` without ever counting it toward `correct` until a parent/Claude review grade is actually merged in. Tested in Tasks 2 and 5.
- **A fill-in-the-blank answer that's correct but differently cased or padded with whitespace** -- `grade_answer` must still mark it correct, not punish a kid for formatting. Tested in Task 2.
- **A second exam taken for a subject** -- `record_exam_report` must accumulate the child's exam history, never overwrite a prior exam's entry, so the dashboard's longitudinal view actually has a history to show. Tested in Task 6.
- **A topic with too few questions to mean anything (e.g. one question)** -- `classify_topic_strength` must report `"insufficient_data"`, never a false "solid" or "needs_work" off a single data point. Tested in Task 5.
- **An exam whose questions span more than one subject/topic tag** -- `aggregate_topic_results` must break results down by each question's own tag, not lump everything under the exam's single declared subject/topic. Tested in Task 5.

---

## Task 1: `scripts/exam_schema.py` -- the question and exam record shapes

**Files:**
- Create: `skills/study-coach/scripts/exam_schema.py`
- Test: `skills/study-coach/tests/test_exam_schema.py`

**Interfaces:**
- Produces: `QUESTION_TYPES = {"multiple_choice", "single_select", "true_false", "fill_in_blank", "matching", "open_response"}` module constant. `make_question(question_id: str, type: str, subject: str, topic: str, prompt: str, options=None, correct_answer=None, competency: str | None = None) -> dict` returning `{"question_id", "type", "subject", "topic", "competency", "prompt", "options", "correct_answer"}` with exactly those keys; raises `ValueError` if `type` not in `QUESTION_TYPES`. `make_exam(exam_id: str, child_id: str, subject: str, topic: str, grade: str, questions: list[dict]) -> dict` returning `{"exam_id", "child_id", "subject", "topic", "grade", "questions"}`; raises `ValueError` if `questions` is empty.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exam_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.exam_schema'`

- [ ] **Step 3: Implement `make_question` and `make_exam` in `scripts/exam_schema.py`**

Straightforward dict builders plus the two validations above.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/exam_schema.py skills/study-coach/tests/test_exam_schema.py
git commit -m "feat(study-coach): exam question and exam record schema"
```

---

## Task 2: `scripts/grading.py` -- per-type grading, never guessing open response

**Files:**
- Create: `skills/study-coach/scripts/grading.py`
- Test: `skills/study-coach/tests/test_grading.py`

**Interfaces:**
- Consumes: question/exam dicts shaped by Task 1's `make_question`/`make_exam`.
- Produces: `is_self_gradable(question: dict) -> bool` -- `False` only for `question["type"] == "open_response"`. `grade_answer(question: dict, given_answer) -> bool | None` -- `None` for `open_response` (always, regardless of `given_answer`); for `fill_in_blank`, `True` if `given_answer`, stripped and casefolded, equals any entry in `correct_answer` (a list) stripped and casefolded the same way; for `matching`, `given_answer == correct_answer` (both dicts) exactly; for every other type, `given_answer == correct_answer` exactly. `score_exam(exam: dict, answers: dict[str, object]) -> list[dict]` -- one `{"question_id", "subject", "topic", "competency", "type", "given_answer", "correct"}` per question in `exam["questions"]`, in that order; `given_answer = answers.get(question_id)` (a missing key yields `None`, graded like any other wrong answer, never treated as "skip this question"); `correct = grade_answer(question, given_answer)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_grading.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.grading'`

- [ ] **Step 3: Implement `is_self_gradable`, `grade_answer`, and `score_exam` in `scripts/grading.py`**

`grade_answer` dispatches on `question["type"]` with the three branches above (`open_response` → `None`; `fill_in_blank` → normalized membership in `correct_answer`; everything else, including `matching`, → exact `==`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/grading.py skills/study-coach/tests/test_grading.py
git commit -m "feat(study-coach): per-type exam grading, open response never guessed"
```

---

## Task 3: `scripts/exam_page.py` -- the self-contained exam HTML page

**Files:**
- Create: `skills/study-coach/scripts/exam_page.py`
- Test: `skills/study-coach/tests/test_exam_page.py`

**Interfaces:**
- Consumes: exam dicts shaped by Task 1's `make_exam`.
- Produces: `render_exam_html(exam: dict) -> str` -- a self-contained HTML document (no external resources, no network) that: embeds the exam verbatim as JSON inside `<script type="application/json" id="exam-data">...</script>`; renders one input control per question tagged `data-question-id="<question_id>"` (radio buttons for `multiple_choice`/`single_select`/`true_false`, a pair of `<select>` elements for `matching`, a text `<input>` for `fill_in_blank`, a `<textarea>` for `open_response`), with every question's `prompt` and any `options` text HTML-escaped (`html.escape`) before being written into the page; includes one `<script>` block implementing client-side self-grading (the same normalization `grading.grade_answer` uses for `fill_in_blank`: trim and lower-case; exact match for every other self-gradable type; nothing for `open_response`) and a "Download results" control that serializes one `{question_id, given_answer, correct}` record per question (`correct: null` for `open_response`) into a client-downloaded JSON file via a `Blob` and an anchor click -- no network call anywhere. Raises `ValueError` for a question whose `type` isn't one of `exam_schema.QUESTION_TYPES`, rather than silently rendering nothing for it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exam_page.py
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
        q = make_question("q1", "fill_in_blank", "matematica", "fracciones", "2 < 3 & 3 > 2, ___?")
        exam = make_exam("exam1", "mateo", "matematica", "fracciones", "3", [q])

        html = render_exam_html(exam)

        self.assertNotIn("2 < 3 & 3 > 2", html)
        self.assertIn("2 &lt; 3 &amp; 3 &gt; 2", html)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.exam_page'`

- [ ] **Step 3: Implement `render_exam_html` in `scripts/exam_page.py`**

Build the page as an f-string/template: a small per-type dispatch dict mapping each `exam_schema.QUESTION_TYPES` member to a function returning that question's HTML fragment, raising `ValueError` on an unmapped type. Use `html.escape` on every piece of question-supplied text before interpolating it. Embed `json.dumps(exam)` verbatim inside the `#exam-data` script tag. The self-grading/download-results `<script>` block is static JS (reads `#exam-data`, reads each `[data-question-id]` control's value, applies the two grading rules above, builds the results JSON, triggers the download) -- write it once as a string constant, not per-question.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/exam_page.py skills/study-coach/tests/test_exam_page.py
git commit -m "feat(study-coach): self-contained exam HTML page with client-side self-grading"
```

---

## Task 4: `scripts/results.py` -- parsing the results export and merging a review grade

**Files:**
- Create: `skills/study-coach/scripts/results.py`
- Test: `skills/study-coach/tests/test_results.py`

**Interfaces:**
- Consumes: nothing at import time; the shape it parses matches what `exam_page.py`'s download-results script writes and what `grading.score_exam` produces -- a JSON list of dicts, each with at least a `"question_id"` key.
- Produces: `parse_results_export(path: Path) -> list[dict]` -- reads and `json.loads`s the file at `path`; raises `ValueError` with a clear message if the parsed JSON isn't a list, or any element isn't a dict with a `"question_id"` key (never silently returns a wrong shape to the rest of the pipeline). `needs_review(results: list[dict]) -> list[str]` -- the `question_id`s where `"correct"` is `None`. `apply_review_grades(results: list[dict], grades: dict[str, bool]) -> list[dict]` -- a new list (does not mutate the input) with each `question_id` in `grades` merged into that entry's `"correct"` field; a `question_id` present in `grades` but absent from `results` is ignored, never invented as a new entry.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_results.py
import json
import tempfile
import unittest
from pathlib import Path
from scripts.results import apply_review_grades, needs_review, parse_results_export

class ParseResultsExportTests(unittest.TestCase):
    def test_parses_a_well_formed_results_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "results.json"
            path.write_text(json.dumps([{"question_id": "q1", "given_answer": True, "correct": True}]), encoding="utf-8")

            results = parse_results_export(path)

            self.assertEqual(results, [{"question_id": "q1", "given_answer": True, "correct": True}])

    def test_rejects_a_file_that_is_not_a_list_of_question_records(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "results.json"
            path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                parse_results_export(path)

class NeedsReviewTests(unittest.TestCase):
    def test_lists_only_the_ungraded_open_response_questions(self):
        results = [
            {"question_id": "q1", "given_answer": True, "correct": True},
            {"question_id": "q2", "given_answer": "a paragraph", "correct": None},
        ]

        self.assertEqual(needs_review(results), ["q2"])

class ApplyReviewGradesTests(unittest.TestCase):
    def test_merges_a_grade_into_the_matching_question_without_touching_others(self):
        results = [
            {"question_id": "q1", "given_answer": True, "correct": True},
            {"question_id": "q2", "given_answer": "a paragraph", "correct": None},
        ]

        updated = apply_review_grades(results, {"q2": False})

        self.assertTrue(updated[0]["correct"])
        self.assertFalse(updated[1]["correct"])

    def test_ignores_a_grade_for_a_question_id_not_present_in_results(self):
        results = [{"question_id": "q1", "given_answer": True, "correct": True}]

        updated = apply_review_grades(results, {"ghost": False})

        self.assertEqual(updated, results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.results'`

- [ ] **Step 3: Implement `parse_results_export`, `needs_review`, and `apply_review_grades` in `scripts/results.py`**

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/results.py skills/study-coach/tests/test_results.py
git commit -m "feat(study-coach): parse the results export, merge open-response review grades"
```

---

## Task 5: `scripts/report.py` -- per-topic strength and the gap report

**Files:**
- Create: `skills/study-coach/scripts/report.py`
- Test: `skills/study-coach/tests/test_report.py`

**Interfaces:**
- Consumes: `score_exam`-shaped (or `apply_review_grades`-updated) results: a list of dicts with `"subject"`, `"topic"`, and `"correct"` keys.
- Produces: `aggregate_topic_results(results: list[dict]) -> dict[str, dict]` -- keyed by `f"{subject}/{topic}"`, valued `{"subject", "topic", "correct", "total"}`; `total` counts every result for that key, `correct` counts only entries where `"correct"` is `True` (a `None` entry -- not yet reviewed -- counts toward `total`, never toward `correct`, so an unreviewed open-response question can never inflate or deflate a score). `classify_topic_strength(correct: int, total: int, min_questions: int = 2) -> str` -- `"insufficient_data"` if `total < min_questions`; else `"needs_work"` if `correct / total < 0.7`; else `"solid"`. `gap_report(aggregated: dict[str, dict]) -> list[dict]` -- one `{"subject", "topic", "correct", "total", "strength"}` per `aggregated` entry, sorted by `correct / total` ascending (weakest first); `"insufficient_data"` entries sort last regardless of their raw ratio, since there's nothing actionable to report from them yet.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.report'`

- [ ] **Step 3: Implement `aggregate_topic_results`, `classify_topic_strength`, and `gap_report` in `scripts/report.py`**

`gap_report`'s sort key: `(aggregated_entry["correct"] / total if total else 0, 0)` for a real ratio, versus a key that always sorts after every real ratio for `insufficient_data` -- e.g. sort on `(1, 0)` if `total < min_questions` else `(0, correct/total)`, so insufficient-data entries land last regardless of their raw numbers. Compute `strength` via `classify_topic_strength` for each entry before sorting.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/report.py skills/study-coach/tests/test_report.py
git commit -m "feat(study-coach): per-topic strength classification and the gap report"
```

---

## Task 6: `scripts/dashboard.py` -- accumulating exam history and the longitudinal `index.html`

**Files:**
- Create: `skills/study-coach/scripts/dashboard.py`
- Test: `skills/study-coach/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `child_dir` return values (Plan 1's `scripts/workspace.py`, already merged); `gap_report`-shaped entries (Task 5).
- Produces: `record_exam_report(child_dir: Path, exam_id: str, subject: str, topic: str, taken_at: str, topic_reports: list[dict]) -> Path` -- appends one `{"exam_id", "subject", "topic", "taken_at", "topic_reports"}` entry to `<child_dir>/subjects/<subject>/exam_history.json` (reads the existing JSON list first if the file exists, writes the appended list back; creates the file and its parent directory on the first call) -- never overwrites a prior exam's entry; returns the history file's path. `render_dashboard_html(workspace: Path) -> str` -- for every child directory under `<workspace>/children/`, for every `exam_history.json` under that child's `subjects/*/`, renders one table of that subject's exam history (most recent first) with exam date, topic, correct/total, and strength; a child with no exam history yet still gets a (mostly empty) section, never a crash; writes the result to `<workspace>/index.html` and also returns the same HTML string.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard.py
import json
import tempfile
import unittest
from pathlib import Path
from scripts.dashboard import record_exam_report, render_dashboard_html
from scripts.workspace import child_dir, resolve_workspace

class RecordExamReportTests(unittest.TestCase):
    def test_creates_the_history_file_on_the_first_exam(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")

            history_path = record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [
                {"subject": "lenguaje", "topic": "sustantivos", "correct": 3, "total": 4, "strength": "solid"},
            ])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["exam_id"], "exam1")

    def test_a_second_exam_for_the_same_subject_accumulates_rather_than_replacing(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [])

            history_path = record_exam_report(mateo, "exam2", "lenguaje", "adjetivos", "2026-10-25", [])

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual([h["exam_id"] for h in history], ["exam1", "exam2"])

class RenderDashboardHtmlTests(unittest.TestCase):
    def test_renders_every_childs_exam_history_and_writes_index_html(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            record_exam_report(mateo, "exam1", "lenguaje", "sustantivos", "2026-10-18", [
                {"subject": "lenguaje", "topic": "sustantivos", "correct": 3, "total": 4, "strength": "solid"},
            ])

            html = render_dashboard_html(workspace)

            self.assertIn("mateo", html)
            self.assertIn("sustantivos", html)
            self.assertEqual((workspace / "index.html").read_text(encoding="utf-8"), html)

    def test_a_child_with_no_exams_yet_does_not_crash_the_dashboard(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            child_dir(workspace, "mateo")

            html = render_dashboard_html(workspace)

            self.assertIn("mateo", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.dashboard'`

- [ ] **Step 3: Implement `record_exam_report` and `render_dashboard_html` in `scripts/dashboard.py`**

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/dashboard.py skills/study-coach/tests/test_dashboard.py
git commit -m "feat(study-coach): accumulating exam history and the longitudinal dashboard"
```

---

## Task 7: CLI entry point, SKILL.md, DISPOSITION.md, evals, README update

**Files:**
- Create: `skills/study-coach/scripts/audit_exam.py` (dev-time CLI; not a kid/parent-facing command)
- Modify: `skills/study-coach/SKILL.md`
- Modify: `skills/study-coach/DISPOSITION.md`
- Modify: `skills/study-coach/evals/evals.json`
- Test: `skills/study-coach/tests/test_audit_exam.py`
- Modify: `README.md` (update the `study-coach` row)

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: `python3 -m scripts.audit_exam render <exam.json> <out.html>` -- loads an exam JSON file, calls `render_exam_html`, writes it to `<out.html>`. `python3 -m scripts.audit_exam score <exam.json> <results.json> <workspace> <child_id> <taken_at>` -- loads the exam and an already-self-graded results export, runs `needs_review` (prints any ungraded open-response `question_id`s as a warning line), aggregates via `aggregate_topic_results` + `gap_report`, prints the gap report, records it via `record_exam_report` (using `child_dir(resolve_workspace(workspace), child_id)`), and re-renders `render_dashboard_html`.

No CI change needed this task -- Plan 1 already wired a `study-coach regression tests` step covering the whole `tests/` directory in all three OS jobs.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_audit_exam.py
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

_EXAM = {
    "exam_id": "exam1", "child_id": "mateo", "subject": "lenguaje", "topic": "sustantivos", "grade": "4",
    "questions": [{
        "question_id": "q1", "type": "true_false", "subject": "lenguaje", "topic": "sustantivos",
        "competency": None, "prompt": "Perro is a noun.", "options": None, "correct_answer": True,
    }],
}

class AuditExamCliTests(unittest.TestCase):
    def test_render_writes_a_self_contained_html_file(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            out_path = Path(root) / "exam.html"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_exam", "render", str(exam_path), str(out_path)],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("Perro is a noun.", out_path.read_text(encoding="utf-8"))

    def test_score_reports_a_gap_and_updates_the_dashboard(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            results_path = Path(root) / "results.json"
            results_path.write_text(json.dumps([{"question_id": "q1", "given_answer": False, "correct": False}]), encoding="utf-8")
            workspace = Path(root) / "family"

            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_exam", "score", str(exam_path), str(results_path), str(workspace), "mateo", "2026-10-18"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("needs_work", result.stdout)
            self.assertTrue((workspace / "children" / "mateo" / "subjects" / "lenguaje" / "exam_history.json").exists())
            self.assertTrue((workspace / "index.html").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with a `CalledProcessError` (module doesn't exist yet)

- [ ] **Step 3: Implement the `scripts/audit_exam.py` CLI**

`main()` parses `sys.argv[1]` as the subcommand (`render` or `score`) and dispatches. `render`: `json.loads` the exam file, `render_exam_html`, write to the output path. `score`: `json.loads` the exam file, `parse_results_export` the results file, print `needs_review(results)` if non-empty, `aggregate_topic_results` + `gap_report`, print each gap-report row, `resolve_workspace` + `child_dir`, `record_exam_report` with the exam's own `subject`/`topic` and the given `taken_at`, then `render_dashboard_html`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Update `SKILL.md`**

Add a new section documenting the exam engine's public surface (`make_question`/`make_exam`, `grade_answer`/`score_exam`, `render_exam_html`, `parse_results_export`/`needs_review`/`apply_review_grades`, `aggregate_topic_results`/`classify_topic_strength`/`gap_report`, `record_exam_report`/`render_dashboard_html`) alongside the existing grounding section. State explicitly: this plan's code never writes question *content* -- the orchestrating skill (Plan 3) generates grounded prompts/options/correct answers at runtime and calls these functions; flashcards, video, and the parent-facing `study-coach` commands (full-bundle/quick-answer) are still not built. Update "What this skill does not do" accordingly.

- [ ] **Step 6: Update `DISPOSITION.md`**

Add a "Plan 2 scope decisions" section recording the two judgment calls this plan makes that the spec explicitly left to the builder: the topic-tagging taxonomy (a `subject/topic` string key, matching Plan 1's own grounding vocabulary, with an optional free-text `competency` field for finer-grained tagging when the content-generating agent wants it -- no separate formal competency hierarchy in v1) and the strength thresholds (`insufficient_data` below 2 questions, `needs_work` below 70%, `solid` at or above 70%) -- both sized small per the spec's explicit "start simple" permission, both revisitable once real exam data exists.

- [ ] **Step 7: Update `evals/evals.json`**

Add scenarios: `open-response-never-silently-graded` (verified-live -- Task 2 and Task 5's `None`-handling tests), `unreviewed-answer-never-inflates-a-topic-score` (verified-live -- Task 5), `exam-history-accumulates-not-overwrites` (verified-live -- Task 6), `insufficient-data-never-reported-as-solid-or-needs-work` (verified-live -- Task 5).

- [ ] **Step 8: Update the `study-coach` row in `README.md`**

Keep the existing sentence about El Salvador/MINEDUCYT grounding; add that the exam engine (question types, self-grading, topic-tagged gap report, accumulating dashboard) now exists too, and that flashcards and the two parent-facing entry points are still follow-up PRs.

- [ ] **Step 9: Run the full test suite**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: all tests across Tasks 1-7 PASS, pristine output

- [ ] **Step 10: Commit**

```bash
git add skills/study-coach/scripts/audit_exam.py skills/study-coach/SKILL.md skills/study-coach/DISPOSITION.md skills/study-coach/evals/evals.json skills/study-coach/tests/test_audit_exam.py README.md
git commit -m "feat(study-coach): exam engine CLI, docs, and evals"
```

---

## Self-Review

**1. Spec coverage:** Question types and the self-grading split (Task 2 -- exact spec wording). Topic/competency tagging every question regardless of type (Task 1 defines the fields, Task 2/5 carry and aggregate them). The results-export-and-reingest flow (Task 3 produces the export, Task 4 parses and merges review grades). The parent gap report (Task 5). Dashboard update / longitudinal `index.html` (Task 6). "No backend" honored throughout -- `exam_page.py` makes no network call and writes nothing; the only writes happen later, driven by the parent bringing the results file back (Tasks 4-6). The confidence-building low-stakes-practice mechanic and the engagement/game layer are **not** in this plan -- both are explicitly Plan 3 territory per the agreed build order (flashcards + the two entry points), noted in `SKILL.md` so it doesn't overclaim.

**2. Step scan:** every code step gives the exact signature and the values the spec pins (question types, the grading rules, the strength thresholds); no step says "handle edge cases" or leaves a type undefined.

**3. Type consistency:** every module that touches a question dict uses the exact key set Task 1's `make_question` defines (`question_id`/`type`/`subject`/`topic`/`competency`/`prompt`/`options`/`correct_answer`); every module that touches a scored result uses Task 2's `score_exam` key set (`question_id`/`subject`/`topic`/`competency`/`type`/`given_answer`/`correct`). `report.py`'s aggregated-entry shape (`subject`/`topic`/`correct`/`total`) is fixed in Task 5 and consumed unchanged by Task 6.

**4. Review Focus:** all five items above (open response at every stage, fill-in-blank normalization, accumulating exam history, insufficient-data classification, multi-topic exam aggregation) have an owning task and an explicit test, listed above.

**5. Proportion:** seven tasks, each a small, focused module plus its test; code shown is signatures, fixed values, and test assertions, not full bodies, except the two short per-type dispatch notes in Tasks 2 and 3 whose exact rules the spec itself pins.
