---
name: study-coach
description: Build a curriculum-grounded learning bundle (video/flashcards/exam) for a specific child, for a school subject or any other topic -- grounded against El Salvador's official MINEDUCYT curriculum where it has real coverage, the family's own Santillana textbook (via parent-supplied photos) where MINEDUCYT's coverage has gaps, or general high-trust sources for a non-curricular topic. Includes a self-grading exam engine (question types, topic-tagged gap report, accumulating per-child dashboard). Flashcards, video, and the two parent-facing entry points (full-bundle/quick-answer) are not yet built (tracked separately). The family's actual workspace (kids' names, grades, exam history, Santillana photos) lives outside this repo by default; the skill code ships here, the data never does.
---

A new skill, not an extension of `teach` (a different shape of problem: solo adult learner, no video/exam/gamification/curriculum-grounding). Full design in `docs/superpowers/specs/2026-10-18-study-coach-design.md`; this skill tracks that spec's "Plan 1" (workspace + grounding) and "Plan 2" (exam engine) of 3 (+1 deferred video plan).

## What exists so far

The grounding/workspace foundation (Plan 1) and the exam engine (Plan 2). **Not yet built:** flashcards, video, the parent-facing "full bundle" and "quick answer" entry points -- those are Plan 3 (see the spec). This plan's code never writes question *content* -- the orchestrating skill (Plan 3) generates grounded prompts/options/correct answers at runtime, via `ground_topic` below, and calls the functions documented here; this plan only validates, renders, grades, aggregates, and persists whatever it's handed.

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

- `make_question(question_id, type, subject, topic, prompt, options=None, correct_answer=None, competency=None) -> dict` and `make_exam(exam_id, child_id, subject, topic, grade, questions) -> dict` build the question/exam records every other module reads. `type` is one of `exam_schema.QUESTION_TYPES` (`multiple_choice`, `single_select`, `true_false`, `fill_in_blank`, `matching`, `open_response`).
- `grade_answer(question, given_answer) -> bool | None` and `score_exam(exam, answers) -> list[dict]` grade per type; `open_response` always grades `None` (never guessed), `fill_in_blank` normalizes case/whitespace, everything else compares exactly.
- `render_exam_html(exam) -> str` builds a self-contained static HTML exam page (no network, no backend): client-side self-grading for every self-gradable type, and a "Download results" button that exports one `{question_id, given_answer, correct}` record per question as a downloadable JSON file.
- `parse_results_export(path) -> list[dict]`, `needs_review(results) -> list[str]`, and `apply_review_grades(results, grades) -> list[dict]` parse that downloaded file and merge in a parent/Claude review grade for any still-`None` open-response item.
- `aggregate_topic_results(results) -> dict`, `classify_topic_strength(correct, total, min_questions=2) -> str`, and `gap_report(aggregated) -> list[dict]` turn scored (and, where needed, enriched with each question's own `subject`/`topic` from the exam -- the downloaded results file doesn't carry those, only `question_id`/`given_answer`/`correct`) results into the per-topic gap report the design doc asks for by name. A topic with fewer than 2 questions reports `"insufficient_data"` rather than a false "solid"/"needs_work".
- `record_exam_report(child_dir, exam_id, subject, topic, taken_at, topic_reports) -> Path` appends (never overwrites) to that child's `exam_history.json`; `render_dashboard_html(workspace) -> str` renders and writes the family's `index.html` from every child's accumulated history.

### Manual inspection CLI (`scripts/audit_exam.py`)

Not a parent/kid-facing command -- development-time tools for exercising the exam pipeline:

```bash
python3 -m scripts.audit_exam render <exam.json> <out.html>
python3 -m scripts.audit_exam score <exam.json> <results.json> <workspace> <child_id> <taken_at>
```

`render` writes the exam's self-contained HTML page. `score` parses an already-self-graded results export, prints any question needing a parent/Claude review, prints the gap report, records it to the child's dashboard, and re-renders `index.html`.

## What this skill does not do (yet)

- Does not generate video or flashcards -- that's Plan 3, not yet written.
- Does not expose a parent-facing "full bundle" or "quick answer" command -- those ship with Plan 3.
- Does not implement the confidence-building low-stakes-practice mechanic or the engagement/game layer -- both are Plan 3 territory per the design doc's agreed build order.
- Does not implement a second country's curriculum, or any TTS/video pipeline -- the video pipeline is deferred to its own later issue per the design doc.
