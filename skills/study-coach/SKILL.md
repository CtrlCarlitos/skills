---
name: study-coach
description: Build a curriculum-grounded learning bundle (video/flashcards/exam) for a specific child, for a school subject or any other topic -- grounded against El Salvador's official MINEDUCYT curriculum where it has real coverage, the family's own Santillana textbook (via parent-supplied photos) where MINEDUCYT's coverage has gaps, or general high-trust sources for a non-curricular topic. This plan ships only the workspace + grounding foundation (resolve_workspace, child_dir, ground_topic) -- video/flashcard/exam generation and the two parent-facing entry points are not yet built (tracked separately). The family's actual workspace (kids' names, grades, exam history, Santillana photos) lives outside this repo by default; the skill code ships here, the data never does.
---

A new skill, not an extension of `teach` (a different shape of problem: solo adult learner, no video/exam/gamification/curriculum-grounding). Full design in `docs/superpowers/specs/2026-10-18-study-coach-design.md`; this skill tracks that spec's "Plan 1 of 3" (+1 deferred video plan).

## What exists so far

Only the grounding/workspace foundation. **Not yet built:** the full-bundle and quick-answer entry points, exam generation, flashcards, video, parent gap reports -- those are separate, later plans (see the spec).

### Workspace (`scripts/workspace.py`)

- `resolve_workspace(path: Path) -> Path` -- creates (idempotently) the family's home workspace: `<path>/children/`, `<path>/sources/mineducyt/`, `<path>/sources/santillana/`, `<path>/assets/`. Safe to call on every invocation; never resets existing data.
- `child_dir(workspace: Path, child_id: str) -> Path` -- creates (idempotently) `<workspace>/children/<child_id>/subjects/`, one partition per kid. Resolving an existing child again never clobbers their data.

Point this at a path **outside this repo** -- `CtrlCarlitos/skills` is a public GitHub repo, and the family's real data (names, grades, exam history, textbook photos) must never be committed or pushed.

### Grounding (`scripts/grounding.py`, `scripts/mineducyt.py`, `scripts/santillana.py`, `scripts/sources.py`)

- `ground_topic(workspace, subject, topic, grade, is_curricular, santillana_photo_path=None, download=None) -> {"sources": [...], "gap": str | None}` -- the one function the rest of the skill (exam/flashcard/video generation, once built) calls to find out what backs a topic. For a curricular topic: tries the MINEDUCYT registry first, then any Santillana photo supplied this call or already cached for that subject/topic. If nothing is found, returns a non-`None` `gap` string -- a curricular topic with no source is always surfaced, never silently treated as "nothing needed." For a non-curricular topic (`is_curricular=False`), skips both and returns `{"sources": [], "gap": None}` -- a clean signal to use general sources, distinguishable from a real gap.
- MINEDUCYT coverage is a small, hand-maintained registry (`mineducyt.REGISTRY`) of known-good URLs, not a web crawler -- currently seeded with Matemática grades 2-3 only, confirmed live during the spec's research. Everything else (notably Lenguaje grades 3-5, this family's actual gap) returns `None` and falls through to Santillana or the gap signal.
- Santillana photos are ad hoc and accumulating: `record_santillana_photo` never overwrites a prior photo for the same subject/topic, it adds to what's cached there.
- Every source returned is a `make_source(...)` dict (`origin`/`title`/`url_or_path`/`cached_path`/`subject`/`topic`/`grade`), individually citable via `format_citation(source)` -- so generated material can always state which source backed which part.

### Manual inspection CLI (`scripts/audit_grounding.py`)

Not a parent/kid-facing command -- a development-time tool for checking what `ground_topic` returns for a given input:

```bash
python3 -m scripts.audit_grounding <workspace> <subject> <topic> <grade> [--general] [--photo <path>]
```

Prints each source's citation, or `gap: <message>` if nothing was found.

## What this skill does not do (yet)

- Does not generate video, flashcards, or exams -- that's Plan 2 (exam engine) and Plan 3 (flashcards + the two entry points), not yet written.
- Does not expose a parent-facing "full bundle" or "quick answer" command -- those ship with Plan 3.
- Does not implement a second country's curriculum, or any TTS/video pipeline -- the video pipeline is deferred to its own later issue per the design doc.
