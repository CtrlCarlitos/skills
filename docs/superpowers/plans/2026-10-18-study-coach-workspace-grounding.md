# study-coach: Workspace + Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `study-coach` skill's foundation: a multi-child home workspace (outside this repo by default) and a curriculum-grounding layer that cites MINEDUCYT where it has real coverage, falls back to parent-supplied Santillana photos where it doesn't, and cleanly signals "use general sources" for non-curricular topics -- never silently proceeding without a source for a curricular claim.

**Architecture:** `sources.py` defines one shared record shape every grounding path returns. `workspace.py` owns creating/resolving the home workspace and per-child partitions -- pure filesystem operations, no network. `mineducyt.py` is a small, hand-maintained registry of known-good MINEDUCYT URLs (not a web crawler) plus a download-and-cache function. `santillana.py` stores and retrieves parent-supplied photos, accumulating rather than overwriting. `grounding.py` is the only thing that decides *which* of those applies for a given request, and is the only function the rest of the skill (Plans 2-3) calls directly.

**Tech Stack:** Python 3 stdlib only (`urllib.request` for the one real network call; no new third-party dependency, so no `requirements.txt`).

**Spec:** `docs/superpowers/specs/2026-10-18-study-coach-design.md` (this is Plan 1 of 3 for the spec's "study-coach v1"; the exam engine and flashcards+entry-points plans follow separately, and the video pipeline is deferred to its own later issue per the user's explicit confirmation).

## Global Constraints

- Workspace location defaults to **outside this repo** -- every function here takes an explicit `workspace: Path` argument; nothing hardcodes or assumes a path inside `skills/study-coach/`.
- The workspace is **multi-child-aware** by design, not incidentally -- each child gets their own partition; nothing pools two children's data together.
- MINEDUCYT coverage is **known to be incomplete** for this family's actual grade range (confirmed in the spec's Constraints: Lenguaje grades 3-5 has no official guide as of this design). `grounding.py` must never treat "no MINEDUCYT entry" as "no grounding needed" -- it's a gap that has to be surfaced, not swallowed.
- Santillana photo supply is **ad hoc and accumulating** -- supplying a new photo for a subject/topic adds to what's cached there, it never silently replaces or deletes a prior supply.
- No real network calls in tests, anywhere -- every function that fetches over the network takes an injectable `download` (or equivalent) parameter, matching this repo's own established convention (`run=subprocess.run` in every other skill here).

## Review Focus

- **A workspace path that doesn't exist yet at all** (the very first time the skill is ever invoked for a family) -- `resolve_workspace` must create the full structure, not assume it's already there. Tested in Task 2.
- **A `child_id` that already has existing data, resolved again later** -- `child_dir` must not clobber or reset an existing child's partition just because it's being resolved again. Tested in Task 2.
- **The common case: no MINEDUCYT registry entry for the requested subject+grade at all** -- `fetch_mineducyt_source` must return a clear "not found" signal (`None`), never a fabricated or best-guess source. Tested in Task 3.
- **A second Santillana photo supplied for a subject/topic that already has one cached** -- must accumulate (both retrievable afterward), never overwrite the first one into oblivion. Tested in Task 4.
- **A non-curricular topic request (`is_curricular=False`)** -- `ground_topic` must skip MINEDUCYT/Santillana entirely and return a clean "use general sources" result, not an empty-looking result indistinguishable from "curricular, but nothing found." Tested in Task 5.

---

## Task 1: `scripts/sources.py` -- the shared source-citation record

**Files:**
- Create: `skills/study-coach/scripts/__init__.py` (empty)
- Create: `skills/study-coach/scripts/sources.py`
- Test: `skills/study-coach/tests/__init__.py` (empty)
- Test: `skills/study-coach/tests/test_sources.py`

**Interfaces:**
- Produces: `make_source(origin: str, title: str, url_or_path: str, cached_path: str | None = None, subject: str | None = None, topic: str | None = None, grade: str | None = None) -> dict` returning `{"origin", "title", "url_or_path", "cached_path", "subject", "topic", "grade"}` with exactly those keys, `origin` one of `"mineducyt"`, `"santillana"`, `"general"`. `format_citation(source: dict) -> str` -- a one-line, human-readable citation string.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sources.py
import unittest
from scripts.sources import make_source, format_citation

class MakeSourceTests(unittest.TestCase):
    def test_builds_a_source_record_with_all_fields(self):
        source = make_source("mineducyt", "Libro de texto 3.° grado", "https://www.mined.gob.sv/.../3.pdf", cached_path="/cache/mat3.pdf", subject="matematica", topic="fracciones", grade="3")
        self.assertEqual(source, {
            "origin": "mineducyt", "title": "Libro de texto 3.° grado",
            "url_or_path": "https://www.mined.gob.sv/.../3.pdf", "cached_path": "/cache/mat3.pdf",
            "subject": "matematica", "topic": "fracciones", "grade": "3",
        })

class FormatCitationTests(unittest.TestCase):
    def test_renders_a_one_line_citation(self):
        source = make_source("mineducyt", "Libro de texto 3.° grado", "https://www.mined.gob.sv/x.pdf")
        citation = format_citation(source)
        self.assertIn("Libro de texto 3.° grado", citation)
        self.assertIn("https://www.mined.gob.sv/x.pdf", citation)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.sources'`

- [ ] **Step 3: Implement `make_source` and `format_citation` in `scripts/sources.py`**

`make_source` returns the dict literally shaped as above (optional params default to `None`). `format_citation` returns `f"{source['title']} -- {source['url_or_path']}"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/__init__.py skills/study-coach/scripts/sources.py skills/study-coach/tests/__init__.py skills/study-coach/tests/test_sources.py
git commit -m "feat(study-coach): shared source-citation record"
```

---

## Task 2: `scripts/workspace.py` -- home workspace + per-child partitions

**Files:**
- Create: `skills/study-coach/scripts/workspace.py`
- Test: `skills/study-coach/tests/test_workspace.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `resolve_workspace(path: Path) -> Path` -- creates `<path>/`, `<path>/children/`, `<path>/sources/mineducyt/`, `<path>/sources/santillana/`, `<path>/assets/` if any are missing (safe to call repeatedly); returns `Path(path)`. `child_dir(workspace: Path, child_id: str) -> Path` -- creates `<workspace>/children/<child_id>/subjects/` if missing; returns `<workspace>/children/<child_id>`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_workspace.py
import tempfile
import unittest
from pathlib import Path
from scripts.workspace import child_dir, resolve_workspace

class ResolveWorkspaceTests(unittest.TestCase):
    def test_creates_the_full_structure_when_nothing_exists_yet(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            self.assertTrue((workspace / "children").is_dir())
            self.assertTrue((workspace / "sources" / "mineducyt").is_dir())
            self.assertTrue((workspace / "sources" / "santillana").is_dir())
            self.assertTrue((workspace / "assets").is_dir())

    def test_is_safe_to_call_again_on_an_existing_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "family"
            resolve_workspace(path)
            (path / "children" / "marker.txt").write_text("keep me", encoding="utf-8")

            resolve_workspace(path)

            self.assertEqual((path / "children" / "marker.txt").read_text(encoding="utf-8"), "keep me")

class ChildDirTests(unittest.TestCase):
    def test_creates_a_childs_partition(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = child_dir(workspace, "mateo")

            self.assertEqual(result, workspace / "children" / "mateo")
            self.assertTrue((result / "subjects").is_dir())

    def test_resolving_an_existing_child_again_does_not_clobber_their_data(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            first = child_dir(workspace, "mateo")
            (first / "subjects" / "note.txt").write_text("existing progress", encoding="utf-8")

            second = child_dir(workspace, "mateo")

            self.assertEqual(first, second)
            self.assertEqual((second / "subjects" / "note.txt").read_text(encoding="utf-8"), "existing progress")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.workspace'`

- [ ] **Step 3: Implement `resolve_workspace` and `child_dir` in `scripts/workspace.py`**

Use `Path.mkdir(parents=True, exist_ok=True)` for every directory created -- idempotent by construction, which is what makes both "doesn't exist yet" and "already exists" safe without a branch.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/workspace.py skills/study-coach/tests/test_workspace.py
git commit -m "feat(study-coach): home workspace and per-child partitions"
```

---

## Task 3: `scripts/mineducyt.py` -- known-source registry + fetch/cache

**Files:**
- Create: `skills/study-coach/scripts/mineducyt.py`
- Test: `skills/study-coach/tests/test_mineducyt.py`

**Interfaces:**
- Consumes: `make_source` (Task 1).
- Produces: `REGISTRY: dict[tuple[str, str], dict]` module constant, keyed `(subject, grade)` (both lowercase strings), valued `{"title": str, "url": str}`. Seeded with the two MINEDUCYT sources confirmed live during this spec's research: `("matematica", "2"): {"title": "Libro de texto 2.° grado, Tomo 2", "url": "https://www.mined.gob.sv/materiales/2026/MATEMATICA/2.%20Libros%20de%20texto/Libro%20de%20texto%202.%C2%B0%20grado_Tomo%202.pdf"}` and `("matematica", "3"): {"title": "Libro de texto 3.° grado", "url": "https://www.mined.gob.sv/materiales/2026/MATEMATICA/2.%20Libros%20de%20texto/Libro%20de%20texto%203.%C2%B0%20grado.pdf"}`. `fetch_mineducyt_source(subject: str, grade: str, cache_dir: Path, download=_default_download) -> dict | None` -- looks up `REGISTRY[(subject.lower(), grade)]`; returns `None` if absent. If present, downloads to `<cache_dir>/<subject>-<grade>.pdf` via `download(url) -> bytes` only if that file doesn't already exist in `cache_dir`, then returns `make_source("mineducyt", title, url, cached_path=str(cached_file), subject=subject, grade=grade)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mineducyt.py
import tempfile
import unittest
from pathlib import Path
from scripts.mineducyt import fetch_mineducyt_source

class FetchMineducytSourceTests(unittest.TestCase):
    def test_returns_none_when_there_is_no_registry_entry(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            result = fetch_mineducyt_source("lenguaje", "4", Path(cache_dir), download=lambda url: b"unused")

            self.assertIsNone(result)

    def test_downloads_and_caches_a_registered_source(self):
        calls = []
        def fake_download(url):
            calls.append(url)
            return b"%PDF-fake-bytes"

        with tempfile.TemporaryDirectory() as cache_dir:
            result = fetch_mineducyt_source("matematica", "3", Path(cache_dir), download=fake_download)

            self.assertEqual(result["origin"], "mineducyt")
            self.assertEqual(result["subject"], "matematica")
            self.assertEqual(result["grade"], "3")
            self.assertEqual(len(calls), 1)
            self.assertTrue(Path(result["cached_path"]).read_bytes().startswith(b"%PDF"))

    def test_does_not_re_download_an_already_cached_source(self):
        calls = []
        def fake_download(url):
            calls.append(url)
            return b"%PDF-fake-bytes"

        with tempfile.TemporaryDirectory() as cache_dir:
            fetch_mineducyt_source("matematica", "3", Path(cache_dir), download=fake_download)
            fetch_mineducyt_source("matematica", "3", Path(cache_dir), download=fake_download)

            self.assertEqual(len(calls), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.mineducyt'`

- [ ] **Step 3: Implement `REGISTRY` and `fetch_mineducyt_source` in `scripts/mineducyt.py`**

`_default_download(url)` wraps `urllib.request.urlopen(url).read()`, used as `download`'s default so production calls hit the real network but every test injects a fake. `cache_dir.mkdir(parents=True, exist_ok=True)` before writing.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/mineducyt.py skills/study-coach/tests/test_mineducyt.py
git commit -m "feat(study-coach): MINEDUCYT known-source registry with fetch/cache"
```

---

## Task 4: `scripts/santillana.py` -- ad hoc, accumulating photo ingestion

**Files:**
- Create: `skills/study-coach/scripts/santillana.py`
- Test: `skills/study-coach/tests/test_santillana.py`

**Interfaces:**
- Consumes: `make_source` (Task 1).
- Produces: `record_santillana_photo(workspace: Path, subject: str, topic: str, photo_path: Path) -> dict` -- copies `photo_path` into `<workspace>/sources/santillana/<subject>/<topic>/`, under a name that never collides with an existing file there (so a second supply for the same subject/topic is added, not overwritten), returns a `make_source("santillana", ..., cached_path=..., subject=subject, topic=topic)`. `find_cached_santillana_sources(workspace: Path, subject: str, topic: str) -> list[dict]` -- one source dict per photo already cached at that subject/topic, empty list if none.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_santillana.py
import tempfile
import unittest
from pathlib import Path
from scripts.santillana import find_cached_santillana_sources, record_santillana_photo
from scripts.workspace import resolve_workspace

class RecordSantillanaPhotoTests(unittest.TestCase):
    def test_records_a_photo_and_it_is_findable_afterward(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page1.jpg"
            photo.write_bytes(b"fake-jpeg-bytes")

            source = record_santillana_photo(workspace, "lenguaje", "sustantivos", photo)

            self.assertEqual(source["origin"], "santillana")
            self.assertEqual(source["subject"], "lenguaje")
            self.assertEqual(source["topic"], "sustantivos")
            self.assertTrue(Path(source["cached_path"]).read_bytes() == b"fake-jpeg-bytes")
            found = find_cached_santillana_sources(workspace, "lenguaje", "sustantivos")
            self.assertEqual(len(found), 1)

    def test_a_second_photo_for_the_same_subject_and_topic_accumulates_rather_than_replacing(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo1 = Path(root) / "page1.jpg"
            photo1.write_bytes(b"first-photo")
            photo2 = Path(root) / "page2.jpg"
            photo2.write_bytes(b"second-photo")

            record_santillana_photo(workspace, "lenguaje", "sustantivos", photo1)
            record_santillana_photo(workspace, "lenguaje", "sustantivos", photo2)

            found = find_cached_santillana_sources(workspace, "lenguaje", "sustantivos")
            cached_bytes = {Path(s["cached_path"]).read_bytes() for s in found}
            self.assertEqual(len(found), 2)
            self.assertEqual(cached_bytes, {b"first-photo", b"second-photo"})

class FindCachedSantillanaSourcesTests(unittest.TestCase):
    def test_returns_empty_list_when_nothing_is_cached_for_that_topic(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            self.assertEqual(find_cached_santillana_sources(workspace, "matematica", "fracciones"), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.santillana'`

- [ ] **Step 3: Implement `record_santillana_photo` and `find_cached_santillana_sources` in `scripts/santillana.py`**

Destination directory: `workspace / "sources" / "santillana" / subject / topic`, `mkdir(parents=True, exist_ok=True)`. Collision-free naming: count existing files in that directory and name the new one `f"{len(existing)+1:03d}{photo_path.suffix}"`. `find_cached_santillana_sources` lists that directory's files (empty list if the directory doesn't exist) and builds one source dict per file via `make_source`, using the file's own name as `title`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/santillana.py skills/study-coach/tests/test_santillana.py
git commit -m "feat(study-coach): ad hoc, accumulating Santillana photo ingestion"
```

---

## Task 5: `scripts/grounding.py` -- the one function everything else calls

**Files:**
- Create: `skills/study-coach/scripts/grounding.py`
- Test: `skills/study-coach/tests/test_grounding.py`

**Interfaces:**
- Consumes: `fetch_mineducyt_source` (Task 3), `record_santillana_photo` + `find_cached_santillana_sources` (Task 4).
- Produces: `ground_topic(workspace: Path, subject: str, topic: str, grade: str, is_curricular: bool, santillana_photo_path: Path | None = None, download=None) -> dict` returning `{"sources": list[dict], "gap": str | None}`. `download` is passed through to `fetch_mineducyt_source` only when not `None` (lets tests inject a fake without this function needing its own default).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_grounding.py
import tempfile
import unittest
from pathlib import Path
from scripts.grounding import ground_topic
from scripts.workspace import resolve_workspace

class GroundTopicTests(unittest.TestCase):
    def test_non_curricular_topic_skips_mineducyt_and_santillana_entirely(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = ground_topic(workspace, "youtube", "channel-setup", grade="n/a", is_curricular=False)

            self.assertEqual(result, {"sources": [], "gap": None})

    def test_curricular_topic_with_a_mineducyt_match_uses_it(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = ground_topic(
                workspace, "matematica", "fracciones", grade="3", is_curricular=True,
                download=lambda url: b"%PDF-fake",
            )

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "mineducyt")
            self.assertIsNone(result["gap"])

    def test_curricular_topic_with_no_mineducyt_entry_and_no_photo_reports_a_gap(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")

            result = ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True)

            self.assertEqual(result["sources"], [])
            self.assertIsNotNone(result["gap"])

    def test_curricular_topic_with_no_mineducyt_entry_but_a_supplied_photo_uses_the_photo(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")

            result = ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True, santillana_photo_path=photo)

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "santillana")
            self.assertIsNone(result["gap"])

    def test_curricular_topic_reuses_an_already_cached_photo_without_a_new_supply(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = resolve_workspace(Path(root) / "family")
            photo = Path(root) / "page.jpg"
            photo.write_bytes(b"photo-bytes")
            ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True, santillana_photo_path=photo)

            result = ground_topic(workspace, "lenguaje", "sustantivos", grade="4", is_curricular=True)

            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["origin"], "santillana")
            self.assertIsNone(result["gap"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.grounding'`

- [ ] **Step 3: Implement `ground_topic` in `scripts/grounding.py`**

If `not is_curricular`: return `{"sources": [], "gap": None}` immediately. Otherwise: build `sources = []`; call `fetch_mineducyt_source(subject, grade, workspace / "sources" / "mineducyt", **({"download": download} if download else {}))`, append if not `None`. If `santillana_photo_path` given, call `record_santillana_photo(...)` and append its result. Then call `find_cached_santillana_sources(...)`; append any not already represented by the just-recorded photo (avoid double-counting the one just added this call -- compare by `cached_path`). If `sources` is still empty, set `gap` to a short descriptive string (e.g. `"no MINEDUCYT coverage and no Santillana photo supplied for lenguaje/sustantivos grade 4"`); otherwise `gap = None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/study-coach/scripts/grounding.py skills/study-coach/tests/test_grounding.py
git commit -m "feat(study-coach): ground_topic orchestrates MINEDUCYT/Santillana/general"
```

---

## Task 6: CLI entry point, SKILL.md, DISPOSITION.md, evals, README, CI wiring

**Files:**
- Create: `skills/study-coach/scripts/audit_grounding.py` (CLI entry point for manual inspection during development; not a kid/parent-facing command)
- Create: `skills/study-coach/SKILL.md`
- Create: `skills/study-coach/DISPOSITION.md`
- Create: `skills/study-coach/evals/evals.json`
- Test: `skills/study-coach/tests/test_audit_grounding.py`
- Modify: `README.md` (add the skill-table row)
- Modify: `.github/workflows/ci.yml` (add a `study-coach regression tests` step per OS job, mirroring the existing per-skill steps)

**Interfaces:**
- Consumes: `ground_topic` (Task 5).
- Produces: `python3 -m scripts.audit_grounding <workspace> <subject> <topic> <grade> [--general] [--photo <path>]` -- calls `ground_topic` with the given arguments and prints the result (each source's citation via `format_citation`, or the gap message) to stdout.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_audit_grounding.py
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

class AuditGroundingCliTests(unittest.TestCase):
    def test_reports_a_gap_for_an_uncovered_curricular_topic(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_grounding", workspace, "lenguaje", "sustantivos", "4"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertIn("gap", result.stdout.lower())

    def test_reports_a_general_topic_with_no_gap(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.audit_grounding", workspace, "youtube", "channel-setup", "n/a", "--general"],
                cwd=_SKILL_ROOT, capture_output=True, text=True, check=True,
            )

            self.assertNotIn("gap", result.stdout.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: FAIL with a `CalledProcessError` (module doesn't exist yet)

- [ ] **Step 3: Implement the `scripts/audit_grounding.py` CLI**

`main()` parses `sys.argv`: positional `workspace, subject, topic, grade`, flags `--general` (sets `is_curricular=False`) and `--photo <path>`. Calls `resolve_workspace` then `ground_topic`. Prints `format_citation(s)` for each source in the result, or `f"gap: {result['gap']}"` if `gap` is not `None`. `if __name__ == "__main__": main()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Write `SKILL.md`**

Frontmatter `name: study-coach`, a `description` covering: builds a learning bundle (video/flashcards/exam, this plan covers only the grounding/workspace foundation) for a specific child against official curriculum where it exists or parent-supplied materials where it doesn't; mention El Salvador/MINEDUCYT by name since that's the only grounding source implemented so far, and that the workspace lives outside this repo by default. Body: document `resolve_workspace`/`child_dir`/`ground_topic` as the current public surface, note explicitly that the exam/flashcard/video generation this skill will eventually drive is **not yet built** (Plans 2/3, tracked in separate issues) -- this plan ships the foundation only, and `SKILL.md` must not overclaim finished functionality it doesn't have yet.

- [ ] **Step 6: Write `DISPOSITION.md`**

Mirror `skills/deliver/DISPOSITION.md`'s shape: an "Audit summary" (why a new skill, not an extension of `teach` -- cite the design doc's own reasoning), a "Scope decisions (confirmed with the user before implementation)" section recording the design doc's key decisions verbatim (two entry points, dual grounding strategy, multi-child workspace, out-of-repo data location, exam-format/question-type decisions even though exam itself isn't built yet in this plan -- so the next plan's reader has the full context in one place), and a note that this is Plan 1 of 3 (+1 deferred) per the design doc.

- [ ] **Step 7: Write `evals/evals.json`**

Shape matches `skills/deliver/evals/evals.json` (`{"scenarios": [...]}`, each `{"id", "category", "description", "status"}`). Include at minimum: `mineducyt-gap-never-silently-passes` (verified-live -- Task 5's gap tests are exactly this), `santillana-photos-accumulate-not-overwrite` (verified-live -- Task 4), `non-curricular-topic-skips-curriculum-sources` (verified-live -- Task 5), `workspace-never-lives-inside-this-repo-by-default` (documented-not-yet-run -- needs a live check once Plan 3's actual entry-point commands exist to invoke with a default path and confirm where they write).

- [ ] **Step 8: Add the skill-table row to `README.md`**

Insert a new row following the exact format of the existing rows: skill name linked to `SKILL.md`, one sentence covering what it does so far (grounding/workspace foundation; full bundle generation lands in follow-up PRs), explicitly note it's El Salvador/MINEDUCYT-specific for now per the design doc's own non-goals.

- [ ] **Step 9: Add the CI step to `.github/workflows/ci.yml`**

In each of the three OS jobs, add a step shaped like the existing per-skill steps (`working-directory: skills/study-coach`, `run: python3 -m unittest discover -s tests -v` on Linux/macOS, `python -m unittest discover -s tests -v` on the Windows job -- match whichever interpreter name that job's existing steps already use), named `study-coach regression tests`.

- [ ] **Step 10: Run the full test suite**

Run: `cd skills/study-coach && python3 -m unittest discover -s tests -v`
Expected: all tests across Tasks 1-6 PASS, pristine output

- [ ] **Step 11: Commit**

```bash
git add skills/study-coach/scripts/audit_grounding.py skills/study-coach/SKILL.md skills/study-coach/DISPOSITION.md skills/study-coach/evals/evals.json skills/study-coach/tests/test_audit_grounding.py README.md .github/workflows/ci.yml
git commit -m "feat(study-coach): CLI entry point, SKILL.md, DISPOSITION.md, evals, CI wiring"
```

---

## Self-Review

**1. Spec coverage:** Multi-child workspace (Task 2). Out-of-repo-by-default workspace location (Task 6's SKILL.md documents it; every function already takes an explicit `workspace` path rather than assuming one, satisfying the actual constraint -- there's no code path that could default into this repo). Dual grounding strategy, MINEDUCYT-then-Santillana-then-gap for curricular topics, general-sources passthrough for non-curricular (Task 5). Ad hoc, accumulating Santillana ingestion (Task 4). "State which source backed which part" (every returned source dict carries its own `origin`/`title`/`url_or_path`, individually citable via `format_citation`). Exam/flashcard/video generation, the parent report, and the two user-facing entry points are explicitly **not** in this plan's scope -- they're Plans 2 and 3, named as such in SKILL.md so it doesn't overclaim.

**2. Step scan:** every code step gives the exact signature and the values the spec pins (the two real registry URLs, the exact directory names); no step says "handle edge cases" or leaves a type undefined.

**3. Type consistency:** every function that returns a source uses `make_source`'s exact shape from Task 1 (`mineducyt.py`, `santillana.py`, `grounding.py`'s own list all build via that one function, never a hand-rolled dict). `grounding.py`'s `ground_topic` return shape (`{"sources", "gap"}`) is fixed in Task 5 and not altered by Task 6, which only consumes it.

**4. Review Focus:** all five items above (empty workspace, re-resolved existing child, missing MINEDUCYT entry, accumulating Santillana photos, non-curricular skip) have an owning task and an explicit test, listed above.

**5. Proportion:** six tasks, each a small, focused module plus its test; code shown is signatures, fixed values, and test assertions, not full bodies, except the two short formatting one-liners the spec's own exact values fully determine.
