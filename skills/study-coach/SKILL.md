---
name: study-coach
description: Build a curriculum-grounded learning bundle (flashcards/exam, video deferred) for a specific child, for a school subject or any other topic -- grounded against El Salvador's official MINEDUCYT curriculum where it has real coverage, the family's own Santillana textbook (via parent-supplied photos) where MINEDUCYT's coverage has gaps, or general high-trust sources for a non-curricular topic. Includes a self-grading exam engine with a confidence-building practice mode, a digital flashcard deck with wrong-answer resurfacing, and the two parent-facing entry points: "full bundle" (subject+topic in, exam+flashcards out) and "quick answer" (one stuck question in, flashcards out). The family's actual workspace (kids' names, grades, exam history, Santillana photos) lives outside this repo by default; the skill code ships here, the data never does. Video is deferred to its own later issue; printable flashcards are deferred as an optional nice-to-have.
---

A new skill, not an extension of `teach` (a different shape of problem: solo adult learner, no video/exam/gamification/curriculum-grounding). Full design in `docs/superpowers/specs/2026-10-18-study-coach-design.md`. This skill now covers all three planned increments of "study-coach v1" -- Plan 1 (workspace + grounding), Plan 2 (exam engine), Plan 3 (flashcards + entry points) -- with video deferred to its own later issue.

## What exists so far

Grounding/workspace (Plan 1), the exam engine with its confidence-building practice mode (Plan 2 + this plan), flashcards with an engagement layer (this plan), and the two parent-facing entry points, documented below as recipes for the invoking Claude session to follow (see "Entry points"). **This skill's code never writes question or flashcard content** -- the invoking session generates grounded prompts/options/answers at runtime, via `ground_topic`, and calls the functions documented here; the code only validates, renders, grades, tracks, and persists whatever it's handed.

### Workspace (`scripts/workspace.py`)

- `resolve_workspace(path: Path) -> Path` -- creates (idempotently) the family's home workspace: `<path>/children/`, `<path>/sources/mineducyt/`, `<path>/sources/santillana/`, `<path>/assets/`. Safe to call on every invocation; never resets existing data.
- `child_dir(workspace: Path, child_id: str) -> Path` -- creates (idempotently) `<workspace>/children/<child_id>/subjects/`, one partition per kid. Resolving an existing child again never clobbers their data.

Point this at a path **outside this repo** -- `CtrlCarlitos/skills` is a public GitHub repo, and the family's real data (names, grades, exam history, textbook photos) must never be committed or pushed.

### Grounding (`scripts/grounding.py`, `scripts/mineducyt.py`, `scripts/santillana.py`, `scripts/sources.py`)

- `ground_topic(workspace, subject, topic, grade, is_curricular, santillana_photo_path=None, download=None) -> {"sources": [...], "gap": str | None}` -- the one function the rest of the skill (exam/flashcard/video generation, once built) calls to find out what backs a topic. For a curricular topic: tries the MINEDUCYT registry first, then any Santillana photo supplied this call or already cached for that subject/topic. If nothing is found, returns a non-`None` `gap` string -- a curricular topic with no source is always surfaced, never silently treated as "nothing needed." For a non-curricular topic (`is_curricular=False`), skips both and returns `{"sources": [], "gap": None}` -- a clean signal to use general sources, distinguishable from a real gap.
- MINEDUCYT coverage is a small, hand-maintained registry (`mineducyt.REGISTRY`) of known-good URLs, not a web crawler -- currently seeded with Matemática grades 2-3 only, confirmed live during the spec's research. Everything else (notably Lenguaje grades 3-5, this family's actual gap) returns `None` and falls through to Santillana or the gap signal.
- Santillana photos are ad hoc and accumulating, cached per **grade** as well as subject/topic: `record_santillana_photo` never overwrites a prior photo for the same subject/topic/grade, it adds to what's cached there, and a photo supplied for one grade is never used to ground a different grade's same-named topic.
- Every source returned is a `make_source(...)` dict (`origin`/`title`/`url_or_path`/`cached_path`/`subject`/`topic`/`grade`), individually citable via `format_citation(source)` -- so generated material can always state which source backed which part.

### Manual inspection CLI (`scripts/audit_grounding.py`)

Not a parent/kid-facing command -- a development-time tool for checking what `ground_topic` returns for a given input:

```bash
python3 -m scripts.audit_grounding <workspace> <subject> <topic> <grade> [--general] [--photo <path>]
```

Prints each source's citation, or `gap: <message>` if nothing was found.

### Exam engine (`scripts/exam_schema.py`, `scripts/grading.py`, `scripts/exam_page.py`, `scripts/results.py`, `scripts/report.py`, `scripts/dashboard.py`)

**`grading.py` is the only place that decides whether an answer is correct** -- the live HTML page's own client-side script independently re-derives the same answer for an immediate on-page check, but nothing downstream trusts it. The real scoring pipeline (`scripts/audit_exam.py`'s `score` subcommand, and anything Plan 3 builds on top of it) always recomputes via `grading.score_exam` from the raw `given_answer` values in the downloaded results file, never from that file's own `correct` field. A fresh review caught this drifting in practice (the page mis-graded every true/false question at one point) -- treat the two implementations as cosmetically similar, never as interchangeable sources of truth.

- `make_question(question_id, type, subject, topic, prompt, options=None, correct_answer=None, competency=None) -> dict` and `make_exam(exam_id, child_id, subject, topic, grade, questions) -> dict` build the question/exam records every other module reads. `type` is one of `exam_schema.QUESTION_TYPES` (`multiple_choice`, `single_select`, `true_false`, `fill_in_blank`, `matching`, `open_response`). Both `make_question` and `render_exam_html` (below) validate `correct_answer`'s shape against `type` via `exam_schema.validate_correct_answer_shape` -- a `fill_in_blank` answer that isn't a list, a `matching` answer that isn't a dict, or a `true_false` answer that isn't a bool raises `ValueError` rather than corrupting grading silently.
- `grade_answer(question, given_answer) -> bool | None` and `score_exam(exam, answers) -> list[dict]` grade per type; `open_response` always grades `None` (never guessed), `fill_in_blank` normalizes case/whitespace, everything else compares exactly.
- `render_exam_html(exam, language="es", mode="exam") -> str` builds a self-contained static HTML exam page (no network, no backend): client-side self-grading for every self-gradable type, and a "Download results" button that exports one `{question_id, given_answer, correct}` record per question as a downloadable JSON file. `language` controls kid-facing labels (True/False, the download button, the matching placeholder) via a small `es`/`en` table -- defaults to Spanish per the spec. `multiple_choice`/`single_select` options render by index, mapped back to the original (correctly-typed) option value on read, so a non-string `correct_answer` still compares correctly; `matching`'s option order is shuffled and every select starts on an empty placeholder, so the answer key is never readable from the page source and an untouched question is never accidentally "correct". **`mode="practice"`** is the confidence-building layer: the same exam, same format, but the entire download/`Blob` mechanism is omitted from the page outright -- a "Show my results" button computes an on-page per-topic score instead, so a practice attempt has no file and no mechanism that could ever reach the real `exam_history.json`/dashboard. Retake it as many times as wanted at zero cost.
- `parse_results_export(path) -> list[dict]`, `needs_review(results) -> list[str]`, and `apply_review_grades(results, grades) -> list[dict]` parse that downloaded file and merge in a parent/Claude review grade for any still-`None` open-response item.
- `aggregate_topic_results(results) -> dict` turns `score_exam`-shaped results (already carrying each question's own `subject`/`topic`) into per-topic `{"subject","topic","correct","total","pending"}` buckets -- a still-ungraded (`None`) result counts as `pending`, never toward `total` or `correct`, so it can neither inflate nor deflate a topic's score before a real review grade exists. `classify_topic_strength(correct, total, min_questions=2) -> str` and `gap_report(aggregated) -> list[dict]` turn that into the per-topic gap report the design doc asks for by name; a topic with fewer than 2 graded questions reports `"insufficient_data"` rather than a false "solid"/"needs_work".
- `record_exam_report(child_dir, exam_id, subject, topic, taken_at, topic_reports) -> Path` appends to that child's `exam_history.json`, replacing any existing entry for the same `exam_id` (so re-scoring after a review-grade merge updates in place) rather than always appending; a genuinely different exam still accumulates. `render_dashboard_html(workspace) -> str` renders and writes the family's `index.html` from every child's accumulated history.

### Manual inspection CLI (`scripts/audit_exam.py`)

Not a parent/kid-facing command -- development-time tools for exercising the exam pipeline:

```bash
python3 -m scripts.audit_exam render <exam.json> <out.html>
python3 -m scripts.audit_exam score <exam.json> <results.json> <workspace> <child_id> <taken_at> [--grades <grades.json>]
```

`render` writes the exam's self-contained HTML page. `score` recomputes every answer's correctness via `grading.score_exam` (ignoring the downloaded file's own `correct` field), optionally merges a `{question_id: bool}` review-grades file for open-response items, prints any question still needing review, prints the gap report, records it to the child's dashboard, and re-renders `index.html`.

### Flashcards (`scripts/flashcard_schema.py`, `scripts/flashcard_history.py`, `scripts/flashcard_page.py`)

- `make_flashcard(card_id, subject, topic, prompt, answer, competency=None) -> dict` and `make_deck(deck_id, child_id, subject, topic, cards) -> dict` build the card/deck records, mirroring `exam_schema.py`'s own shape.
- `render_flashcard_html(deck, language="es") -> str` builds a self-contained digital flip-deck: tap/click a card to reveal its answer, "Got it"/"Missed it" per card updates a live points counter and a streak counter that resets on any miss -- the engagement layer, pure client-side display, never persisted -- and a "Download results" button exports one `{card_id, result}` record per card the kid actually marked (re-marking a card keeps only its latest mark; a card never flipped is simply absent, unlike an unanswered exam question).
- `record_flashcard_session(child_dir, deck_id, subject, topic, reviewed_at, results) -> Path` **always appends** to that child's `flashcard_history.json` -- reviewing the same deck on two different days is two genuinely separate sessions, not a correction to one, the opposite convention from `dashboard.record_exam_report`'s replace-by-`exam_id` and deliberately so. `compute_card_weakness(history) -> dict[str, int]` counts misses per card across every session. `select_cards_for_review(cards, history, max_extra_appearances=1) -> list[dict]` duplicates a previously-missed card (up to `max_extra_appearances` times) so it resurfaces more in the next deck -- a card with no history of misses is never duplicated, and with no history at all the original cards come back unchanged.

### Bundle (`scripts/bundle.py`)

- `topic_dir(child_dir, subject, topic) -> Path`, `write_bundle_files(child_dir, subject, topic, exam_html=None, flashcard_html=None, practice_html=None) -> dict[str, Path]`, and `render_topic_index_html(child_dir, subject, topic, written) -> str` write a topic's **current** materials (`exam.html`/`flashcards.html`/`practice.html` and a landing `index.html` linking whichever exist) -- every write **overwrites**, it never accumulates, the opposite convention from the history files above and deliberately so: this is "what the bundle looks like right now," not a log.

### Manual inspection CLI (`scripts/audit_bundle.py`)

Not a parent/kid-facing command -- a development-time tool for exercising the whole pipeline end to end:

```bash
python3 -m scripts.audit_bundle <workspace> <child_id> <exam.json> <deck.json> [--practice]
```

Renders the exam page (and, with `--practice`, the practice-mode variant too) and the flashcard page, writes them via `write_bundle_files`, renders the topic index, and prints the written paths.

## Entry points

These are recipes for the invoking Claude session, not more Python to call blindly -- the actual question/flashcard *content* has to come from the session's own grounded judgment, using the sources `ground_topic` returns.

**Full bundle** (parent gives a subject + topic + child + grade): call `ground_topic`. If it returns a `gap`, stop and tell the parent what's missing -- never proceed ungrounded for a curricular topic. Otherwise, generate exam questions and flashcards grounded in the returned sources; build them via `make_exam`/`make_question` and `make_deck`/`make_flashcard`; call `select_cards_for_review` against that child's existing `flashcard_history.json` before rendering the deck; render the exam (and, optionally, a practice-mode copy) and the flashcard deck; write them via `write_bundle_files` and render the topic index; tell the parent where the files are. After the kid takes the real exam and the parent brings back the results file (and any review grades for open-response questions), `audit_exam.py score` is the reference pattern for scoring and updating the dashboard.

**Quick answer** (parent gives one stuck question, not a full subject/topic commitment): same grounding discipline, but default to **flashcards only, no exam** -- the spec's own "most likely smaller" judgment call. Typically 1-3 cards answering the specific question, grounded the same way, written the same way (no bundle index needed for something this small; a single `flashcards.html` is enough).

## What this skill does not do

- Does not implement a second country's curriculum, or any TTS/video pipeline -- video is deferred to its own later issue per the design doc.
- Does not implement a printable flashcard export -- the spec marks it secondary/optional ("not a requirement every deck must satisfy equally well"), deferred as a builder decision (see `DISPOSITION.md`).
- Does not implement a formal spaced-repetition algorithm (e.g. SM-2) -- `select_cards_for_review`'s simple miss-count resurfacing is the spec's own "start simple" default, revisit only if it proves insufficient in practice.
