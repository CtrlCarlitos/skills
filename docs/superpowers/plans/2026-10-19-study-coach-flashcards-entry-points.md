# study-coach: Flashcards + Entry Points Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `study-coach` skill's remaining core pieces: a digital flashcard deck with wrong-answer resurfacing, the confidence-building practice-mode variant of the exam engine (a low-stakes, ungraded rehearsal that can never reach the real dashboard), a per-topic bundle that ties grounding + exam + flashcards into files a parent can actually open, and the `SKILL.md` recipes for the two parent-facing entry points (full bundle, quick answer) that tell the orchestrating Claude session how to assemble them from everything Plans 1-2 already built.

**Architecture:** `flashcard_schema.py` defines the card/deck record shape, mirroring `exam_schema.py`'s own pattern. `flashcard_history.py` owns the accumulating per-child review history and the resurfacing decision. `flashcard_page.py` renders the self-contained digital deck (flip-to-reveal, a lightweight points/streak display, a results export) -- the engagement layer. `exam_page.py` gains a `mode="practice"` variant -- the confidence-building layer -- that shows an on-page score breakdown instead of producing any downloadable file, so a practice attempt has no path to the real `exam_history.json`/dashboard by construction, not by convention. `bundle.py` writes a topic's current materials (exam/flashcards/practice page) into the child's workspace and renders a small per-topic landing page linking them. None of this plan's code generates question or flashcard *content* -- that's the orchestrating skill's job at runtime, grounded via Plan 1's `ground_topic`; `SKILL.md`'s new sections are the recipe that tells it how.

**Tech Stack:** Python 3 stdlib only (continuing Plans 1-2's constraint: no new third-party dependency). No network calls anywhere in this plan.

**Spec:** `docs/superpowers/specs/2026-10-18-study-coach-design.md` (this is Plan 3 of 3 for the spec's "study-coach v1"; the video pipeline is deferred to its own later issue). Builds on Plan 1 (`docs/superpowers/plans/2026-10-18-study-coach-workspace-grounding.md`, merged, PR #32) and Plan 2 (`docs/superpowers/plans/2026-10-18-study-coach-exam-engine.md`, merged, PR #33) -- this plan consumes Plan 1's `workspace.py`/`grounding.py` and Plan 2's `exam_schema.py`/`exam_page.py` directly.

## Global Constraints

- **Flashcards are digital-first, verbatim from the spec:** an on-screen deck, tap/click to reveal the answer, tracks which ones the kid keeps getting wrong so those resurface more. A printable export is explicitly secondary/optional and -- per the spec's own "not a requirement every deck must satisfy equally well" -- **out of scope for this plan** (see "What's left to the builder" in the design doc; recorded as a deferred builder decision in `DISPOSITION.md`, not forgotten).
- **The confidence-building layer and the engagement layer are two distinct mechanics, verbatim from the spec:** low-stakes practice that mimics the real exam's format plus a visible progress indicator (confidence), versus points/streaks on the flashcard/review experience (engagement) -- never collapsed into one generic "gamification" feature.
- **"No backend" still holds:** nothing in this plan opens a network connection or runs continuously. Practice-mode results never leave the browser at all (no download, no file) -- the strongest available guarantee that a practice attempt can't contaminate the real gap report.
- **Delivery language stays a parameter, continuing Plan 2:** every kid-facing page here takes the same `language="es"` convention Plan 2 established in `exam_page.py`.
- **Multi-child, continuing Plans 1-2:** every function here that touches the workspace operates on one child's own partition (`child_dir`'s return value).
- **This plan's code never writes question or flashcard content.** It validates, renders, tracks, and persists whatever the orchestrating skill hands it, exactly like Plans 1-2's own scope boundary.

## Review Focus

- **A flashcard missed in an earlier session, reviewed again in a later deck build** -- `select_cards_for_review` must resurface that specific card more than a card never missed, not just return cards in the same order every time. Tested in Task 2.
- **The same deck reviewed in two separate sessions** -- `record_flashcard_session` must accumulate both sessions in the child's history (each review is a genuinely separate event, unlike Plan 2's exam-review-grade correction case), so weakness tracking has real history to work from. Tested in Task 2.
- **A practice-mode exam** -- `render_exam_html(exam, mode="practice")` must have no mechanism that could reach the real dashboard: no download button, no exported file, nothing for a future caller to accidentally feed into `record_exam_report`. Tested in Task 4.
- **A deck with no prior review history at all** -- `select_cards_for_review` must return the original cards unchanged, never inventing a resurfacing artifact when there's nothing to resurface yet. Tested in Task 2.
- **Writing a topic's bundle a second time (e.g. after regenerating content)** -- `write_bundle_files` must overwrite the previous bundle's files cleanly, never accumulate stale duplicates -- the opposite of history files, which must accumulate. Tested in Task 5.

---

## Task 1: `scripts/flashcard_schema.py` -- the card and deck record shapes

**Files:**
- Create: `skills/study-coach/scripts/flashcard_schema.py`
- Test: `skills/study-coach/tests/test_flashcard_schema.py`

**Interfaces:**
- Produces: `make_flashcard(card_id: str, subject: str, topic: str, prompt: str, answer: str, competency: str | None = None) -> dict` returning `{"card_id", "subject", "topic", "competency", "prompt", "answer"}` with exactly those keys. `make_deck(deck_id: str, child_id: str, subject: str, topic: str, cards: list[dict]) -> dict` returning `{"deck_id", "child_id", "subject", "topic", "cards"}`; raises `ValueError` if `cards` is empty.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flashcard_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.flashcard_schema'`

- [ ] **Step 3: Implement `make_flashcard` and `make_deck` in `scripts/flashcard_schema.py`**

Straightforward dict builders plus the one validation, mirroring `exam_schema.make_question`/`make_exam`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/flashcard_schema.py skills/study-coach/tests/test_flashcard_schema.py
git commit -m "feat(study-coach): flashcard and deck record schema"
```

---

## Task 2: `scripts/flashcard_history.py` -- accumulating history and wrong-answer resurfacing

**Files:**
- Create: `skills/study-coach/scripts/flashcard_history.py`
- Test: `skills/study-coach/tests/test_flashcard_history.py`

**Interfaces:**
- Consumes: `child_dir` return values (Plan 1's `scripts/workspace.py`); card dicts shaped by Task 1's `make_flashcard`.
- Produces: `record_flashcard_session(child_dir: Path, deck_id: str, subject: str, topic: str, reviewed_at: str, results: list[dict]) -> Path` -- `results` is `[{"card_id": str, "result": "correct" | "incorrect"}, ...]`, one entry per card the kid actually marked that session (a card never flipped/marked is simply absent -- skipping a flashcard is not the same as missing it, unlike an unanswered exam question). Appends one `{"deck_id", "subject", "topic", "reviewed_at", "results"}` entry to `<child_dir>/subjects/<subject>/flashcard_history.json` every call -- **always appends, never replaces by `deck_id`**, because reviewing the same deck on two different days is two genuinely separate sessions, not a correction to one (contrast with Plan 2's exam-review-grade case). Returns the history file's path. `compute_card_weakness(history: list[dict]) -> dict[str, int]` -- `card_id -> count of "incorrect" results for that card across every session entry`; a card with zero misses is absent from the returned dict. `select_cards_for_review(cards: list[dict], history: list[dict], max_extra_appearances: int = 1) -> list[dict]` -- returns a new list (never mutates `cards`): each card appears once, plus up to `max_extra_appearances` additional times if `compute_card_weakness(history)` shows at least that many misses for it (so a card missed once appears twice total, a card never missed appears once, with `max_extra_appearances=1`); a card with no history of misses at all is never duplicated.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flashcard_history.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.flashcard_history'`

- [ ] **Step 3: Implement `record_flashcard_session`, `compute_card_weakness`, and `select_cards_for_review` in `scripts/flashcard_history.py`**

`record_flashcard_session` mirrors Plan 1/2's own read-existing-list-then-append pattern, with no replace-by-id step (unlike Plan 2's `dashboard.record_exam_report`) -- say so in a short comment, since a future reader who skimmed Plan 2 first will reasonably expect the same dedup and needs to know it was a deliberate omission, not a miss.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/flashcard_history.py skills/study-coach/tests/test_flashcard_history.py
git commit -m "feat(study-coach): accumulating flashcard history and wrong-answer resurfacing"
```

---

## Task 3: `scripts/flashcard_page.py` -- the self-contained digital deck

**Files:**
- Create: `skills/study-coach/scripts/flashcard_page.py`
- Test: `skills/study-coach/tests/test_flashcard_page.py`

**Interfaces:**
- Consumes: deck dicts shaped by Task 1's `make_deck`.
- Produces: `render_flashcard_html(deck: dict, language: str = "es") -> str` -- a self-contained HTML document (no network): embeds the deck verbatim as JSON inside `<script type="application/json" id="deck-data">...</script>` (escaping `</` the same way `exam_page.render_exam_html` does, for the same reason -- a card's own text could otherwise prematurely close that tag); renders one flip-card element per card tagged `data-card-id="<card_id>"`, showing the HTML-escaped `prompt` and, on click/tap, the HTML-escaped `answer`; a "Got it" / "Missed it" button pair per card that updates a live points counter (+1 per "Got it") and a live streak counter (consecutive "Got it" clicks, reset to 0 on any "Missed it") displayed on the page -- the engagement layer, pure client-side, never persisted; a "Download results" button that exports one `{"card_id", "result"}` record **only for cards the kid actually marked this session** (re-marking the same card keeps only its latest mark, never a duplicate entry) as a downloaded JSON file, same `Blob`/anchor-click mechanism as `exam_page.py`. Kid-facing labels ("Got it", "Missed it", "Download results", the points/streak display) come from an `es`/`en` table, defaulting to Spanish, matching `exam_page.py`'s own convention.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flashcard_page.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.flashcard_page'`

- [ ] **Step 3: Implement `render_flashcard_html` in `scripts/flashcard_page.py`**

Follow `exam_page.py`'s own structure closely (it already embodies the lessons from Plan 2's final review -- `</` escaping, `html.escape` on all question-supplied text, an `es`/`en` label table): one card-rendering helper, a static self-contained `<script>` block for flip/mark/points/streak/download, keyed by `card_id` in a JS object (not an array) so a re-mark overwrites rather than duplicates.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/flashcard_page.py skills/study-coach/tests/test_flashcard_page.py
git commit -m "feat(study-coach): self-contained flashcard deck with points/streak engagement layer"
```

---

## Task 4: `scripts/exam_page.py` -- practice mode, the confidence-building layer

**Files:**
- Modify: `skills/study-coach/scripts/exam_page.py`
- Test: `skills/study-coach/tests/test_exam_page.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `render_exam_html(exam: dict, language: str = "es", mode: str = "exam") -> str` -- new `mode` parameter, `"exam"` (default, unchanged behavior) or `"practice"`. In `"practice"` mode: the page is visibly labeled as practice (not graded for real) in the `es`/`en` label table; the "Download results"/`downloadResults()` button and its entire `Blob`-based export path are **omitted from the rendered page outright** (not merely unused -- there must be nothing in the page's own source for a future caller to accidentally wire up); in their place, a "Show my results" button calls a `showResults()` function that computes the same per-question client-side grades `downloadResults()` already computes and renders a per-topic tally into a `<div id="practice-results">` on the page, with no network call and no file ever created. Raises `ValueError` for any `mode` other than `"exam"`/`"practice"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exam_page.py -- add to the existing RenderExamHtmlTests class
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL -- `test_practice_mode_has_no_download_mechanism_at_all` and `test_rejects_an_unknown_mode` fail (`mode` isn't a recognized parameter / behavior doesn't exist yet); `test_exam_mode_is_unaffected_by_the_new_parameter` passes already (documents the no-op default).

- [ ] **Step 3: Implement the `mode` parameter in `render_exam_html`**

Validate `mode in ("exam", "practice")` up front. Keep the existing self-grading script (`gradeAnswer`/`readAnswer`) shared between both modes -- `"practice"` just skips defining/rendering `downloadResults()`/the `Blob` import entirely and defines `showResults()` instead, which iterates `exam.questions`, reuses `readAnswer`/`gradeAnswer`, tallies correct/total per `subject`/`topic` client-side, and writes a plain-text summary into `#practice-results` via `textContent` -- no `Blob`, no anchor, no `URL.createObjectURL`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/exam_page.py skills/study-coach/tests/test_exam_page.py
git commit -m "feat(study-coach): practice mode -- the confidence-building layer, no path to the real dashboard"
```

---

## Task 5: `scripts/bundle.py` -- the current per-topic materials

**Files:**
- Create: `skills/study-coach/scripts/bundle.py`
- Test: `skills/study-coach/tests/test_bundle.py`

**Interfaces:**
- Consumes: `child_dir` return values (Plan 1).
- Produces: `topic_dir(child_dir: Path, subject: str, topic: str) -> Path` -- creates (idempotently) `<child_dir>/subjects/<subject>/<topic>/`; returns it. `write_bundle_files(child_dir: Path, subject: str, topic: str, exam_html: str | None = None, flashcard_html: str | None = None, practice_html: str | None = None) -> dict[str, Path]` -- writes whichever of `exam.html`/`flashcards.html`/`practice.html` are given (not `None`) into `topic_dir(...)`, **overwriting** any existing file of the same name every call -- this is the topic's *current* materials, not a history log, unlike `exam_history.json`/`flashcard_history.json`; returns `{"exam": path, ...}` for whichever were written, omitting keys for arguments left `None`. `render_topic_index_html(child_dir: Path, subject: str, topic: str, written: dict[str, Path]) -> str` -- a small landing page linking whichever of exam/flashcards/practice exist (relative links, by filename), written to `topic_dir(...)/index.html` and also returned as a string.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bundle.py
import tempfile
import unittest
from pathlib import Path
from scripts.bundle import render_topic_index_html, topic_dir, write_bundle_files
from scripts.workspace import child_dir, resolve_workspace

class WriteBundleFilesTests(unittest.TestCase):
    def test_writes_only_the_given_files(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")

            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v1</html>")

            self.assertEqual(set(written), {"exam"})
            self.assertEqual(written["exam"].read_text(encoding="utf-8"), "<html>exam v1</html>")

    def test_a_second_write_overwrites_the_first_rather_than_accumulating(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v1</html>")

            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam v2</html>")

            self.assertEqual(written["exam"].read_text(encoding="utf-8"), "<html>exam v2</html>")
            self.assertEqual(len(list(topic_dir(mateo, "lenguaje", "sustantivos").iterdir())), 1)

class RenderTopicIndexHtmlTests(unittest.TestCase):
    def test_links_only_the_files_that_were_actually_written(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            mateo = child_dir(workspace, "mateo")
            written = write_bundle_files(mateo, "lenguaje", "sustantivos", exam_html="<html>exam</html>", flashcard_html="<html>cards</html>")

            html = render_topic_index_html(mateo, "lenguaje", "sustantivos", written)

            self.assertIn("exam.html", html)
            self.assertIn("flashcards.html", html)
            self.assertNotIn("practice.html", html)
            self.assertEqual((topic_dir(mateo, "lenguaje", "sustantivos") / "index.html").read_text(encoding="utf-8"), html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.bundle'`

- [ ] **Step 3: Implement `topic_dir`, `write_bundle_files`, and `render_topic_index_html` in `scripts/bundle.py`**

`write_bundle_files`'s file names are fixed (`exam.html`, `flashcards.html`, `practice.html`) regardless of language/mode -- there is only ever one *current* bundle per topic, which is the point of overwrite-not-accumulate.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/bundle.py skills/study-coach/tests/test_bundle.py
git commit -m "feat(study-coach): per-topic bundle -- current materials, overwritten not accumulated"
```

---

## Task 6: CLI entry point, SKILL.md entry-point recipes, DISPOSITION.md, evals, README update

**Files:**
- Create: `skills/study-coach/scripts/audit_bundle.py` (dev-time CLI; not a kid/parent-facing command)
- Modify: `skills/study-coach/SKILL.md`
- Modify: `skills/study-coach/DISPOSITION.md`
- Modify: `skills/study-coach/evals/evals.json`
- Test: `skills/study-coach/tests/test_audit_bundle.py`
- Modify: `README.md` (update the `study-coach` row)

**Interfaces:**
- Consumes: everything from Tasks 1-5, plus Plan 1's `ground_topic`/`child_dir` and Plan 2's `exam_schema`/`exam_page`.
- Produces: `python3 -m scripts.audit_bundle <workspace> <child_id> <exam.json> <deck.json> [--practice]` -- loads the exam and deck JSON files, renders the exam page (and, if `--practice` is given, the practice-mode variant too), renders the flashcard page, writes all of them via `write_bundle_files` into that child's topic directory (the exam's own `subject`/`topic`), renders and writes the topic index, and prints the written paths.

No CI change needed this task -- Plan 1 already wired a `study-coach regression tests` step covering the whole `tests/` directory in all three OS jobs.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_audit_bundle.py
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
_DECK = {
    "deck_id": "deck1", "child_id": "mateo", "subject": "lenguaje", "topic": "sustantivos",
    "cards": [{"card_id": "c1", "subject": "lenguaje", "topic": "sustantivos", "competency": None, "prompt": "Perro", "answer": "Sustantivo"}],
}

class AuditBundleCliTests(unittest.TestCase):
    def test_writes_the_exam_and_flashcard_pages_and_the_topic_index(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            deck_path = Path(root) / "deck.json"
            deck_path.write_text(json.dumps(_DECK), encoding="utf-8")
            workspace = Path(root) / "family"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_bundle", str(workspace), "mateo", str(exam_path), str(deck_path)],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            topic = workspace / "children" / "mateo" / "subjects" / "lenguaje" / "sustantivos"
            self.assertIn("Perro is a noun.", (topic / "exam.html").read_text(encoding="utf-8"))
            self.assertIn("Perro", (topic / "flashcards.html").read_text(encoding="utf-8"))
            self.assertFalse((topic / "practice.html").exists())
            self.assertIn("exam.html", (topic / "index.html").read_text(encoding="utf-8"))

    def test_practice_flag_also_writes_a_practice_page(self):
        with tempfile.TemporaryDirectory() as root:
            exam_path = Path(root) / "exam.json"
            exam_path.write_text(json.dumps(_EXAM), encoding="utf-8")
            deck_path = Path(root) / "deck.json"
            deck_path.write_text(json.dumps(_DECK), encoding="utf-8")
            workspace = Path(root) / "family"

            subprocess.run(
                [sys.executable, "-m", "scripts.audit_bundle", str(workspace), "mateo", str(exam_path), str(deck_path), "--practice"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            topic = workspace / "children" / "mateo" / "subjects" / "lenguaje" / "sustantivos"
            self.assertTrue((topic / "practice.html").exists())
            self.assertNotIn("downloadResults", (topic / "practice.html").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with a `CalledProcessError` (module doesn't exist yet)

- [ ] **Step 3: Implement the `scripts/audit_bundle.py` CLI**

`main()` parses the four positional args plus the optional `--practice` flag. Loads `exam.json`/`deck.json`, calls `render_exam_html(exam)` (and `render_exam_html(exam, mode="practice")` if `--practice`), `render_flashcard_html(deck)`, `resolve_workspace` + `child_dir`, `write_bundle_files(...)`, `render_topic_index_html(...)`, then prints each written path.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Write the "Full bundle" and "Quick answer" recipes into `SKILL.md`**

These are instructions for the orchestrating Claude session, not new Python logic -- the actual content generation (question prompts, flashcard answers, all grounded via Plan 1's `ground_topic`) is the invoking session's own job. Document, as a numbered recipe, for **full bundle** (subject + topic + child + grade in): call `ground_topic`; if it returns a `gap`, stop and tell the parent what's missing (never proceed ungrounded for a curricular topic); otherwise generate exam questions and flashcards grounded in the returned sources, build them via `make_exam`/`make_question`/`make_deck`/`make_flashcard`, call `select_cards_for_review` against that child's existing flashcard history before rendering, render exam + flashcards (+ practice, optional) via Tasks 3-4's functions, write them via `write_bundle_files`, render the topic index, and tell the parent where the files are. For **quick answer** (one stuck question in, no grade/full-bundle commitment): same grounding discipline, but default to **flashcards only, no exam** (the spec's own "most likely smaller" judgment call, recorded as a builder decision in `DISPOSITION.md`) -- typically 1-3 cards answering the specific question, written the same way. State explicitly that this skill still has no video pipeline (deferred to its own later issue) and no printable flashcard export (deferred, spec marks it optional/secondary).

- [ ] **Step 6: Update `DISPOSITION.md`**

Add a "Plan 3 scope decisions" section recording: the flashcard-print-export deferral (verbatim reasoning above); the confidence-layer mechanic choice (practice mode reuses the real exam's question bank and format, shows an on-page score, never produces a file -- "no mechanism to reach the dashboard" chosen over "a mechanism that's merely not called", since the stronger guarantee is cheap here and the spec's panic-vs-fluency framing makes a false "this counted" scare a real risk to design against); the engagement-layer mechanic (points + a reset-on-miss streak, no levels/badges, sized small per the spec's explicit permission); and quick answer's default shape (flashcards only, no exam, per the spec's own "most likely smaller" wording).

- [ ] **Step 7: Update `evals/evals.json`**

Add scenarios: `weak-flashcards-resurface-more` (verified-live -- Task 2), `flashcard-sessions-accumulate-not-replace` (verified-live -- Task 2, and explicitly note this is the opposite convention from Plan 2's exam dedup, on purpose), `practice-mode-has-no-path-to-the-real-dashboard` (verified-live -- Task 4), `bundle-overwrites-not-accumulates` (verified-live -- Task 5).

- [ ] **Step 8: Update the `study-coach` row in `README.md`**

Keep the existing grounding/exam-engine sentences; add that flashcards and the practice-mode confidence layer now exist too, and that the real parent-facing entry points are documented in `SKILL.md` as recipes for the invoking session (grounded content generation itself is still the orchestrating skill's job, not pre-built here) -- this closes out the "study-coach v1" trilogy per the design doc (video remains its own later issue).

- [ ] **Step 9: Run the full test suite**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: all tests across Tasks 1-6 PASS, pristine output

- [ ] **Step 10: Commit**

```bash
git add skills/study-coach/scripts/audit_bundle.py skills/study-coach/SKILL.md skills/study-coach/DISPOSITION.md skills/study-coach/evals/evals.json skills/study-coach/tests/test_audit_bundle.py README.md
git commit -m "feat(study-coach): flashcard/practice bundle CLI, entry-point recipes, docs, evals"
```

---

## Self-Review

**1. Spec coverage:** Digital-first flashcards with tap-to-reveal and wrong-answer resurfacing (Tasks 1-3). The confidence-building layer -- low-stakes practice in the real exam's own format, with a visible progress indicator (Task 4's on-page `#practice-results` summary). The engagement layer -- points/streaks on the flashcard experience, kept mechanically and conceptually separate from the confidence layer (Task 3's client-side counters, never touching Task 4's code path). The two entry points -- full bundle and quick answer -- documented as `SKILL.md` recipes (Task 6, Step 5), since the actual content generation is inherently the invoking session's job, not something a plan like this one can pre-build; the recipes are what ties grounding (Plan 1) + exam (Plan 2) + flashcards (this plan) into something runnable, matching the build order's own wording for Plan 3. The printable flashcard export is explicitly out of scope, recorded as a deferred builder decision per the spec's own "secondary, optional... not a requirement" language, not silently dropped.

**2. Step scan:** every code step gives the exact signature and the values this plan pins (the fixed bundle filenames, the `max_extra_appearances` default, the `es`/`en` label requirement); no step says "handle edge cases" or leaves a type undefined.

**3. Type consistency:** every module that builds a card/deck uses Task 1's exact `make_flashcard`/`make_deck` key sets. `flashcard_history.py`'s functions all consume the same `{"card_id", "result"}` shape `flashcard_page.py` exports. `bundle.py`'s `written` dict shape (`{"exam": Path, ...}`) is fixed in Task 5 and consumed unchanged by `render_topic_index_html` and the Task 6 CLI.

**4. Review Focus:** all five items above (resurfacing, session accumulation, practice mode's no-path-to-dashboard guarantee, no-history-yet behavior, bundle overwrite-not-accumulate) have an owning task and an explicit test, listed above.

**5. Proportion:** six tasks, five of them a small focused module (or one targeted modification) plus its test; the sixth ties them together via documentation, which is genuinely this plan's own deliverable for the two entry points, not padding. Code shown is signatures, fixed values, and test assertions, not full bodies, except the short algorithmic notes in Tasks 2-4 whose exact rules this plan itself pins.
