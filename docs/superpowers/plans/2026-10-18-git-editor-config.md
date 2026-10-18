# git-editor-config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `git-editor-config` skill that audits a repo's `.gitattributes`, `.editorconfig`, `.gitignore`, and tracked executable bits against what the repo's actual file content needs, reports gaps as a Markdown matrix, and applies only itemized, explicitly-approved changes.

**Architecture:** A `scan.py` layer gathers raw facts about the repo's tracked files (path, git mode bits, shebang presence, a binary heuristic) with no judgment. Pure classification modules (`classify.py`, `exec_bit.py`) turn one file's raw facts into a suggested rule or drift flag. `gitattributes.py`/`editorconfig.py` parse the repo's *existing* config into pattern lists and answer "is this path already covered?" so the audit reports only gaps, not already-settled rules. `gaps.py` combines all of the above into gap rows; `gitignore_audit.py` is a parallel, narrower check reusing `classify.py`'s binary/generated heuristic. `report.py` renders gap rows as Markdown (repo-policy's exact table convention). `apply.py` is the only place that writes anything, and only for the exact subset of gaps the user names.

**Tech Stack:** Python 3, stdlib only (`subprocess`, `fnmatch`, `pathlib`) — no new third-party dependency, so no `requirements.txt` is needed (confirmed in Task 1).

**Spec:** CtrlCarlitos/skills#18, and the brainstorming playback approved in this conversation (recorded verbatim in `skills/git-editor-config/DISPOSITION.md`'s "Scope decisions" section, written in Task 10).

## Global Constraints

- Never auto-applies. Every write happens only in `apply.py`, only for the exact items a human named — no "apply everything" entry point anywhere in this skill (same rule repo-policy and update-docs already follow in this repo).
- Report gaps only — a file/pattern already covered by an existing `.gitattributes`/`.editorconfig` rule is never re-proposed, so the audit stays useful as the repo grows (issue's explicit "iterate over time" requirement).
- Not a GitHub-governance tool (that's `repo-policy`, #5/#17) and not a generic ecosystem `.gitignore`/`.editorconfig` template fetcher — every suggestion must be grounded in this repo's actual scanned file content (shebang, mode bits, extension), never a boilerplate.
- Dependency-injected `run` (`subprocess.run` by default) on every function that shells out, matching `repo-policy/scripts/inspect.py`'s convention — no test exercises a real git subprocess it didn't itself construct as a throwaway fixture repo.
- Real git fixture repos built in tmp dirs for any test that exercises `scan.py`, `gitignore_audit.py`, or `apply.py` — not mocked subprocess output — matching `release-notes`' established precedent in this repo for git-facing code.

## Review Focus

- **A `*.patch`/`*.diff` file** — the issue names this exact case ("patch files matched against an upstream tree need to stay LF... or `git apply` breaks"). `classify.py` must special-case these extensions to `text eol=lf -diff` rather than falling through to a generic text/binary guess. Tested in Task 3.
- **A large, legitimately-text file (e.g. a minified `.js` bundle) misclassified as binary.** The binary heuristic (null-byte sniffing) must not misfire on long lines of plain text. Tested in Task 3.
- **A file already covered by an existing `.gitattributes` rule must never be re-proposed, even if `classify.py` would suggest something different from the existing rule.** Existing, explicit human-authored coverage always wins; `gaps.py` must filter by coverage *before* classification ever has a chance to disagree with it. Tested in Task 5.
- **Executable-bit drift must stay conservative in the "remove +x" direction.** Flagging a missing `+x` on a shebang script is safe; flagging "remove +x" is only safe for a fixed set of extensions that are unambiguously non-executable by convention (`.md .txt .json .yaml .yml .css .html`) — anything else (including no-shebang `.py`/`.sh`, which are legitimately executable by convention in many repos) must never be flagged for removal, to avoid false-positive churn. Tested in Task 4.
- **`apply.py` must only touch the files/bits named in the approved subset it's given, and must leave everything else in the working tree byte-for-byte unchanged.** Tested in Task 9 by diffing the whole fixture repo before/after an apply call with a partial approval set.

---

## Task 1: Scaffolding + `scan.py` — gather raw per-file facts

**Files:**
- Create: `skills/git-editor-config/scripts/__init__.py` (empty)
- Create: `skills/git-editor-config/scripts/scan.py`
- Test: `skills/git-editor-config/tests/__init__.py` (empty)
- Test: `skills/git-editor-config/tests/test_scan.py`

**Interfaces:**
- Produces: `scan_tracked_files(repo_root: Path, run=subprocess.run) -> list[dict]`, each dict `{"path": str, "mode": str, "has_shebang": bool, "is_binary": bool}`. `path` is relative to `repo_root`, POSIX-separated. `mode` is the raw git mode string from `git ls-files -s` (e.g. `"100755"`, `"100644"`). `has_shebang`: file's first two bytes are `b"#!"`. `is_binary`: a null byte appears in the first 8000 bytes read.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scan.py
import subprocess
from pathlib import Path
from scripts.scan import scan_tracked_files

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

def test_scans_a_real_repo_reporting_mode_shebang_and_binary(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "run.sh").write_text("#!/bin/bash\necho hi\n")
    (repo / "notes.txt").write_text("plain text\n")
    (repo / "photo.png").write_bytes(b"\x89PNG\x00\x01\x02binarydata")
    _git(repo, "add", "-A")
    (repo / "run.sh").chmod(0o755)
    _git(repo, "update-index", "--chmod=+x", "run.sh")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")

    files = {f["path"]: f for f in scan_tracked_files(repo)}

    assert files["run.sh"]["has_shebang"] is True
    assert files["run.sh"]["mode"] == "100755"
    assert files["notes.txt"]["has_shebang"] is False
    assert files["notes.txt"]["is_binary"] is False
    assert files["photo.png"]["is_binary"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_scan.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.scan'` (or similar import error)

- [ ] **Step 3: Implement `scan_tracked_files(repo_root: Path, run=subprocess.run) -> list[dict]` in `scripts/scan.py`**

Use `run(["git", "ls-files", "-s"], cwd=repo_root, capture_output=True, text=True, check=True)`, parse each line (`"<mode> <sha> <stage>\t<path>"`) to get `mode` and `path`. For each path, read up to the first 8000 bytes of `repo_root / path` in binary mode once; derive `has_shebang` (first two bytes `== b"#!"`) and `is_binary` (`b"\x00" in chunk`) from that same read — don't read the file twice.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_scan.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/__init__.py skills/git-editor-config/scripts/scan.py skills/git-editor-config/tests/__init__.py skills/git-editor-config/tests/test_scan.py
git commit -m "feat(git-editor-config): scan tracked files for mode, shebang, binary signal"
```

---

## Task 2: `gitattributes.py` — parse existing rules and check coverage

**Files:**
- Create: `skills/git-editor-config/scripts/gitattributes.py`
- Test: `skills/git-editor-config/tests/test_gitattributes.py`

**Interfaces:**
- Consumes: nothing from Task 1 (pure, string/path input only).
- Produces: `parse_gitattributes(content: str) -> list[dict]`, each dict `{"pattern": str, "attrs": list[str]}` (one entry per non-comment, non-blank line; `attrs` is the whitespace-split remainder). `pattern_matches(pattern: str, path: str) -> bool` — gitignore-glob-style match (delegates to `fnmatch.fnmatch` for a bare pattern like `*.sh`; a pattern containing `/` is matched against the full path with `fnmatch.fnmatch` too). `is_covered(path: str, rules: list[dict]) -> bool` — `True` if any rule's pattern matches `path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gitattributes.py
from scripts.gitattributes import parse_gitattributes, pattern_matches, is_covered

def test_parses_rules_skipping_comments_and_blanks():
    content = "# comment\n*.sh text eol=lf\n\n*.patch text eol=lf -diff\n"
    rules = parse_gitattributes(content)
    assert rules == [
        {"pattern": "*.sh", "attrs": ["text", "eol=lf"]},
        {"pattern": "*.patch", "attrs": ["text", "eol=lf", "-diff"]},
    ]

def test_pattern_matches_a_bare_extension_glob():
    assert pattern_matches("*.sh", "scripts/run.sh") is True
    assert pattern_matches("*.sh", "run.py") is False

def test_is_covered_true_only_when_a_rule_matches():
    rules = [{"pattern": "*.sh", "attrs": ["text", "eol=lf"]}]
    assert is_covered("scripts/run.sh", rules) is True
    assert is_covered("notes.txt", rules) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_gitattributes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gitattributes'`

- [ ] **Step 3: Implement `parse_gitattributes`, `pattern_matches`, `is_covered` in `scripts/gitattributes.py`**

`parse_gitattributes`: split on `\n`, strip each line, skip empty lines and lines starting with `#`, split remaining lines on whitespace, first token is `pattern`, rest is `attrs`. `pattern_matches`: for a bare pattern (no `/`), match against `Path(path).name` with `fnmatch.fnmatch`; for a pattern containing `/`, match the full `path` with `fnmatch.fnmatch`. Document in a module docstring that this is an `fnmatch`-based approximation of git's actual gitignore-glob semantics (no `**` double-star handling, no anchoring edge cases) — good enough for an audit tool's "already covered?" check, not a drop-in replacement for git's own matcher. `is_covered`: `any(pattern_matches(r["pattern"], path) for r in rules)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_gitattributes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/gitattributes.py skills/git-editor-config/tests/test_gitattributes.py
git commit -m "feat(git-editor-config): parse .gitattributes and check pattern coverage"
```

---

## Task 3: `classify.py` — suggest a rule category for one file

**Files:**
- Create: `skills/git-editor-config/scripts/classify.py`
- Test: `skills/git-editor-config/tests/test_classify.py`

**Interfaces:**
- Consumes: one `scan_tracked_files`-shaped dict (Task 1's `{"path", "mode", "has_shebang", "is_binary"}`).
- Produces: `classify_file(file: dict) -> dict | None`, returning `{"attrs": list[str], "reason": str}` or `None` when there's no clear signal (never guesses). `attrs` is the exact `.gitattributes` attribute list to suggest (e.g. `["text", "eol=lf"]`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_classify.py
from scripts.classify import classify_file

def test_shebang_file_suggests_text_eol_lf():
    result = classify_file({"path": "run.sh", "mode": "100755", "has_shebang": True, "is_binary": False})
    assert result["attrs"] == ["text", "eol=lf"]

def test_patch_extension_suggests_text_eol_lf_no_diff():
    result = classify_file({"path": "vendor/foo.patch", "mode": "100644", "has_shebang": False, "is_binary": False})
    assert result["attrs"] == ["text", "eol=lf", "-diff"]

def test_binary_signal_suggests_no_text_no_diff():
    result = classify_file({"path": "logo.png", "mode": "100644", "has_shebang": False, "is_binary": True})
    assert result["attrs"] == ["-text", "-diff"]

def test_large_plain_text_file_is_not_misclassified_as_binary():
    # No null byte in the scanned chunk -- is_binary is False, as scan.py would report
    result = classify_file({"path": "bundle.min.js", "mode": "100644", "has_shebang": False, "is_binary": False})
    assert result is None  # ordinary text file, no shebang, no extension signal -- no clear rule to suggest

def test_ordinary_file_with_no_signal_returns_none():
    result = classify_file({"path": "README.md", "mode": "100644", "has_shebang": False, "is_binary": False})
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_classify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.classify'`

- [ ] **Step 3: Implement `classify_file(file: dict) -> dict | None` in `scripts/classify.py`**

Order of checks (first match wins): (1) `file["path"]` suffix in `(".patch", ".diff")` → `{"attrs": ["text", "eol=lf", "-diff"], "reason": "patch/diff file: must stay LF for `git apply` against an upstream tree, and must not be diffed"}`. (2) `file["is_binary"]` → `{"attrs": ["-text", "-diff"], "reason": "binary content detected (null byte in file)"}`. (3) `file["has_shebang"]` → `{"attrs": ["text", "eol=lf"], "reason": "shebang line: must stay LF or the interpreter line breaks on checkout"}`. (4) otherwise → `None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_classify.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/classify.py skills/git-editor-config/tests/test_classify.py
git commit -m "feat(git-editor-config): classify one file's gitattributes needs from scanned signal"
```

---

## Task 4: `exec_bit.py` — executable-bit drift detection

**Files:**
- Create: `skills/git-editor-config/scripts/exec_bit.py`
- Test: `skills/git-editor-config/tests/test_exec_bit.py`

**Interfaces:**
- Consumes: one `scan_tracked_files`-shaped dict.
- Produces: `exec_bit_drift(file: dict) -> str | None` returning `"missing"` (has shebang, not mode `*755`), `"unexpected"` (mode `*755`, no shebang, and extension is in the fixed non-executable set), or `None` (no drift / ambiguous, not flagged).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exec_bit.py
from scripts.exec_bit import exec_bit_drift

def test_shebang_without_exec_bit_is_missing():
    assert exec_bit_drift({"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False}) == "missing"

def test_shebang_with_exec_bit_is_not_flagged():
    assert exec_bit_drift({"path": "run.sh", "mode": "100755", "has_shebang": True, "is_binary": False}) is None

def test_exec_bit_on_known_non_executable_extension_is_unexpected():
    assert exec_bit_drift({"path": "notes.md", "mode": "100755", "has_shebang": False, "is_binary": False}) == "unexpected"

def test_exec_bit_without_shebang_on_ambiguous_extension_is_not_flagged():
    # .py and .sh are commonly executable by convention even without a shebang in some repos --
    # conservative by design, per the plan's Review Focus: never flag removal for these.
    assert exec_bit_drift({"path": "tool.py", "mode": "100755", "has_shebang": False, "is_binary": False}) is None
    assert exec_bit_drift({"path": "tool.sh", "mode": "100755", "has_shebang": False, "is_binary": False}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_exec_bit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.exec_bit'`

- [ ] **Step 3: Implement `exec_bit_drift(file: dict) -> str | None` in `scripts/exec_bit.py`**

`NON_EXECUTABLE_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".css", ".html"}` module constant. `is_exec = file["mode"].endswith("755")`. If `file["has_shebang"] and not is_exec`: return `"missing"`. If `is_exec and not file["has_shebang"] and Path(file["path"]).suffix in NON_EXECUTABLE_EXTENSIONS`: return `"unexpected"`. Otherwise `None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_exec_bit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/exec_bit.py skills/git-editor-config/tests/test_exec_bit.py
git commit -m "feat(git-editor-config): detect executable-bit drift, conservative on removal"
```

---

## Task 5: `gaps.py` — combine scan + coverage + classification into gap rows

**Files:**
- Create: `skills/git-editor-config/scripts/gaps.py`
- Test: `skills/git-editor-config/tests/test_gaps.py`

**Interfaces:**
- Consumes: `is_covered` (Task 2), `classify_file` (Task 3), `exec_bit_drift` (Task 4).
- Produces: `build_gitattributes_gaps(files: list[dict], existing_rules: list[dict]) -> list[dict]`, each row `{"path": str, "suggested_attrs": list[str], "reason": str}` — only for files where `is_covered(path, existing_rules)` is `False` and `classify_file(file)` is not `None`. `build_exec_bit_gaps(files: list[dict]) -> list[dict]`, each row `{"path": str, "drift": str}` for every file where `exec_bit_drift(file)` is not `None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gaps.py
from scripts.gaps import build_gitattributes_gaps, build_exec_bit_gaps

def test_gitattributes_gap_skips_already_covered_file():
    files = [{"path": "run.sh", "mode": "100755", "has_shebang": True, "is_binary": False}]
    existing_rules = [{"pattern": "*.sh", "attrs": ["text", "eol=lf"]}]
    assert build_gitattributes_gaps(files, existing_rules) == []

def test_gitattributes_gap_reports_uncovered_file_with_signal():
    files = [{"path": "deploy.patch", "mode": "100644", "has_shebang": False, "is_binary": False}]
    gaps = build_gitattributes_gaps(files, existing_rules=[])
    assert len(gaps) == 1
    assert gaps[0]["path"] == "deploy.patch"
    assert gaps[0]["suggested_attrs"] == ["text", "eol=lf", "-diff"]

def test_gitattributes_gap_never_contradicts_an_existing_rule_even_if_classify_would_differ():
    # existing_rules covers run.sh with a DIFFERENT rule than classify_file would suggest --
    # coverage wins; this file must not appear as a gap.
    files = [{"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False}]
    existing_rules = [{"pattern": "*.sh", "attrs": ["-text"]}]
    assert build_gitattributes_gaps(files, existing_rules) == []

def test_exec_bit_gaps_reports_only_files_with_drift():
    files = [
        {"path": "run.sh", "mode": "100644", "has_shebang": True, "is_binary": False},
        {"path": "notes.txt", "mode": "100644", "has_shebang": False, "is_binary": False},
    ]
    gaps = build_exec_bit_gaps(files)
    assert gaps == [{"path": "run.sh", "drift": "missing"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_gaps.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gaps'`

- [ ] **Step 3: Implement `build_gitattributes_gaps` and `build_exec_bit_gaps` in `scripts/gaps.py`**

`build_gitattributes_gaps`: for each file, skip if `is_covered(file["path"], existing_rules)`; else call `classify_file(file)`, skip if `None`, else append `{"path": file["path"], "suggested_attrs": result["attrs"], "reason": result["reason"]}`. `build_exec_bit_gaps`: for each file, call `exec_bit_drift(file)`, skip if `None`, else append `{"path": file["path"], "drift": drift}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_gaps.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/gaps.py skills/git-editor-config/tests/test_gaps.py
git commit -m "feat(git-editor-config): build gitattributes and exec-bit gap rows"
```

---

## Task 6: `editorconfig.py` — parse existing `.editorconfig` and find extension gaps

**Files:**
- Create: `skills/git-editor-config/scripts/editorconfig.py`
- Test: `skills/git-editor-config/tests/test_editorconfig.py`

**Interfaces:**
- Consumes: `pattern_matches` (Task 2, reused — `.editorconfig` section headers use the same glob style).
- Produces: `parse_editorconfig(content: str) -> list[dict]`, each dict `{"pattern": str, "settings": dict}` — one entry per `[pattern]` section header, `settings` built from the `key = value` lines until the next section or EOF (a leading `root = true` line outside any section is ignored). `build_editorconfig_gaps(files: list[dict], existing_sections: list[dict]) -> list[dict]`, one row per *distinct file extension present in `files`* with no matching section, shaped `{"extension": str, "example_path": str}` (one example path per extension, not one row per file, so a repo with 200 `.py` files gets one gap row, not 200).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_editorconfig.py
from scripts.editorconfig import parse_editorconfig, build_editorconfig_gaps

def test_parses_sections_into_pattern_and_settings():
    content = "root = true\n\n[*.py]\nindent_style = space\nindent_size = 4\n\n[*.md]\ntrim_trailing_whitespace = false\n"
    sections = parse_editorconfig(content)
    assert sections == [
        {"pattern": "*.py", "settings": {"indent_style": "space", "indent_size": "4"}},
        {"pattern": "*.md", "settings": {"trim_trailing_whitespace": "false"}},
    ]

def test_gap_reports_one_row_per_uncovered_extension_not_per_file():
    files = [
        {"path": "a.py", "mode": "100644", "has_shebang": False, "is_binary": False},
        {"path": "b.py", "mode": "100644", "has_shebang": False, "is_binary": False},
        {"path": "c.go", "mode": "100644", "has_shebang": False, "is_binary": False},
    ]
    gaps = build_editorconfig_gaps(files, existing_sections=[])
    extensions = {g["extension"] for g in gaps}
    assert extensions == {".py", ".go"}
    assert len(gaps) == 2

def test_gap_skips_extension_already_covered_by_a_section():
    files = [{"path": "a.py", "mode": "100644", "has_shebang": False, "is_binary": False}]
    existing_sections = [{"pattern": "*.py", "settings": {"indent_style": "space"}}]
    assert build_editorconfig_gaps(files, existing_sections) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_editorconfig.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.editorconfig'`

- [ ] **Step 3: Implement `parse_editorconfig` and `build_editorconfig_gaps` in `scripts/editorconfig.py`**

`parse_editorconfig`: iterate lines; a line matching `^\[(.+)\]$` starts a new section (store the bracket contents as `pattern`, reset a fresh `settings` dict); a line matching `key = value` (split on first `=`, strip both sides) adds to the current section's `settings` if a section is open, otherwise it's ignored (covers `root = true`). Append the last open section at the end. `build_editorconfig_gaps`: collect `Path(f["path"]).suffix` for every file, dedupe preserving first-seen order, for each extension check `any(pattern_matches(s["pattern"], f"x{extension}") for s in existing_sections)` using Task 2's `pattern_matches` imported from `scripts.gitattributes` — skip if covered, else append `{"extension": extension, "example_path": <first file path with that extension>}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_editorconfig.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/editorconfig.py skills/git-editor-config/tests/test_editorconfig.py
git commit -m "feat(git-editor-config): parse .editorconfig and find uncovered extensions"
```

---

## Task 7: `gitignore_audit.py` — tracked-generated and unignored-generated detection

**Files:**
- Create: `skills/git-editor-config/scripts/gitignore_audit.py`
- Test: `skills/git-editor-config/tests/test_gitignore_audit.py`

**Interfaces:**
- Consumes: `classify_file` (Task 3) — a file whose `classify_file` result includes `"-text"` or `"-diff"` in `attrs` is this module's definition of "looks generated/binary."
- Produces: `find_tracked_generated_files(files: list[dict]) -> list[dict]`, one row `{"path": str, "reason": str}` per tracked file where `classify_file(file)` returns a binary-shaped result (`attrs` containing `"-text"`) — these are tracked files that look like they should probably be gitignored instead. `find_unignored_generated_files(repo_root: Path, run=subprocess.run) -> list[dict]`, one row `{"path": str}` per **untracked** file reported by `git status --porcelain --ignored=no` whose `classify_file`-equivalent binary signal (same null-byte sniff as `scan.py`, reusing a shared helper) says it looks generated.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gitignore_audit.py
import subprocess
from pathlib import Path
from scripts.gitignore_audit import find_tracked_generated_files, find_unignored_generated_files

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

def test_find_tracked_generated_files_flags_binary_signal():
    files = [
        {"path": "build/out.bin", "mode": "100644", "has_shebang": False, "is_binary": True},
        {"path": "src/main.py", "mode": "100644", "has_shebang": False, "is_binary": False},
    ]
    gaps = find_tracked_generated_files(files)
    assert [g["path"] for g in gaps] == ["build/out.bin"]

def test_find_unignored_generated_files_reports_untracked_binary_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("hello\n")
    _git(repo, "add", "README.md")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")
    (repo / "cache.bin").write_bytes(b"\x00\x01binary")

    gaps = find_unignored_generated_files(repo)

    assert [g["path"] for g in gaps] == ["cache.bin"]

def test_find_unignored_generated_files_skips_already_ignored_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text("*.bin\n")
    (repo / "README.md").write_text("hello\n")
    _git(repo, "add", "README.md", ".gitignore")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")
    (repo / "cache.bin").write_bytes(b"\x00\x01binary")

    assert find_unignored_generated_files(repo) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_gitignore_audit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gitignore_audit'`

- [ ] **Step 3: Implement `find_tracked_generated_files` and `find_unignored_generated_files` in `scripts/gitignore_audit.py`**

`find_tracked_generated_files`: for each file, call `classify_file(file)` (import from `scripts.classify`), skip if `None` or `"-text"` not in `result["attrs"]`, else append `{"path": file["path"], "reason": result["reason"]}`. `find_unignored_generated_files`: run `git status --porcelain --ignored=no -- .` (untracked files show as `"?? <path>"`; this flag set means git won't list ignored files at all, so every `??` line is already un-ignored by definition), parse the paths, for each read up to 8000 bytes and check for a null byte (reuse the exact sniff from `scan.py` — factor it into a small shared `_is_binary(chunk: bytes) -> bool` helper in `scan.py` that both modules import, rather than duplicating the check), keep only binary-signaled ones.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_gitignore_audit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/gitignore_audit.py skills/git-editor-config/tests/test_gitignore_audit.py
git commit -m "feat(git-editor-config): flag tracked-generated and unignored-generated files"
```

---

## Task 8: `report.py` — render all gap categories as Markdown

**Files:**
- Create: `skills/git-editor-config/scripts/report.py`
- Test: `skills/git-editor-config/tests/test_report.py`

**Interfaces:**
- Consumes: the row shapes produced by Tasks 5-7 (`build_gitattributes_gaps`, `build_exec_bit_gaps`, `build_editorconfig_gaps`, `find_tracked_generated_files`, `find_unignored_generated_files`).
- Produces: `render_markdown(gitattributes_gaps: list[dict], exec_bit_gaps: list[dict], editorconfig_gaps: list[dict], gitignore_gaps: list[dict]) -> str` — four Markdown sections with `##` headers (`.gitattributes gaps`, `Executable-bit drift`, `.editorconfig gaps`, `.gitignore gaps`), each a table, and each section omitted entirely (not printed as an empty table) when its input list is empty. If all four lists are empty, returns a single line: `"No gaps found."`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
from scripts.report import render_markdown

def test_renders_only_nonempty_sections():
    output = render_markdown(
        gitattributes_gaps=[{"path": "deploy.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "patch file"}],
        exec_bit_gaps=[],
        editorconfig_gaps=[],
        gitignore_gaps=[],
    )
    assert "## .gitattributes gaps" in output
    assert "deploy.patch" in output
    assert "## Executable-bit drift" not in output

def test_all_empty_reports_no_gaps():
    assert render_markdown([], [], [], []) == "No gaps found."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.report'`

- [ ] **Step 3: Implement `render_markdown(...)` in `scripts/report.py`**

Build a list of `(title, rows, columns)` tuples, skip any with empty `rows`; for each remaining one emit `f"## {title}\n"` plus a Markdown table built the same way `repo-policy/scripts/report.py` does (header row, `|---|...|` separator, one row per item, pipe-escaping every cell value with `.replace("|", r"\|")`). Join sections with `"\n\n"`. If no sections remain, return `"No gaps found."`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/report.py skills/git-editor-config/tests/test_report.py
git commit -m "feat(git-editor-config): render all four gap categories as Markdown"
```

---

## Task 9: `apply.py` — itemized, nothing-else-touched application

**Files:**
- Create: `skills/git-editor-config/scripts/apply.py`
- Test: `skills/git-editor-config/tests/test_apply.py`

**Interfaces:**
- Consumes: the exact row shapes from Tasks 5-7, filtered by the caller down to only the approved subset before calling in.
- Produces: `apply_gitattributes_rules(repo_root: Path, approved: list[dict]) -> None` (appends `f"{row['path']} {' '.join(row['suggested_attrs'])}\n"` per row to `repo_root / ".gitattributes"`, creating the file if absent). `apply_exec_bit_fixes(repo_root: Path, approved: list[dict], run=subprocess.run) -> None` (for each row, `run(["git", "update-index", "--chmod=+x" if row["drift"] == "missing" else "--chmod=-x", row["path"]], cwd=repo_root, check=True)`). `apply_editorconfig_sections(repo_root: Path, approved: list[dict], default_settings: dict) -> None` (appends `f"\n[*{row['extension']}]\n"` plus one `f"{k} = {v}\n"` line per item in `default_settings`, to `repo_root / ".editorconfig"`, creating it with a leading `"root = true\n"` if absent). `apply_gitignore_patterns(repo_root: Path, approved: list[dict]) -> None` (appends `f"{row['path']}\n"` per row to `repo_root / ".gitignore"`, creating it if absent).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_apply.py
import subprocess
from pathlib import Path
from scripts.apply import apply_gitattributes_rules, apply_exec_bit_fixes, apply_editorconfig_sections, apply_gitignore_patterns

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

def test_apply_gitattributes_rules_appends_only_approved_rows(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitattributes").write_text("*.sh text eol=lf\n")

    apply_gitattributes_rules(repo, [{"path": "deploy.patch", "suggested_attrs": ["text", "eol=lf", "-diff"], "reason": "x"}])

    content = (repo / ".gitattributes").read_text()
    assert content == "*.sh text eol=lf\ndeploy.patch text eol=lf -diff\n"

def test_apply_exec_bit_fixes_only_changes_named_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "run.sh").write_text("#!/bin/bash\n")
    (repo / "other.sh").write_text("#!/bin/bash\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")

    apply_exec_bit_fixes(repo, [{"path": "run.sh", "drift": "missing"}])

    modes = subprocess.run(["git", "ls-files", "-s"], cwd=repo, capture_output=True, text=True, check=True).stdout
    assert "100755" in [line.split()[0] for line in modes.splitlines() if line.endswith("run.sh")]
    assert "100644" in [line.split()[0] for line in modes.splitlines() if line.endswith("other.sh")]

def test_apply_only_touches_named_files_rest_of_tree_untouched(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("hello\n")
    (repo / "run.sh").write_text("#!/bin/bash\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")
    readme_before = (repo / "README.md").read_bytes()

    apply_exec_bit_fixes(repo, [{"path": "run.sh", "drift": "missing"}])

    assert (repo / "README.md").read_bytes() == readme_before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_apply.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.apply'`

- [ ] **Step 3: Implement the four `apply_*` functions in `scripts/apply.py`**

Each function does exactly the one file operation described in its Interfaces entry above and nothing else — no function in this module may iterate over anything other than the `approved` list it was given.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_apply.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/git-editor-config/scripts/apply.py skills/git-editor-config/tests/test_apply.py
git commit -m "feat(git-editor-config): itemized apply for gitattributes, exec bits, editorconfig, gitignore"
```

---

## Task 10: `audit.py` CLI entry point, SKILL.md, DISPOSITION.md, evals, CI wiring

**Files:**
- Create: `skills/git-editor-config/scripts/audit.py`
- Create: `skills/git-editor-config/SKILL.md`
- Create: `skills/git-editor-config/DISPOSITION.md`
- Create: `skills/git-editor-config/evals/evals.json`
- Test: `skills/git-editor-config/tests/test_audit.py`
- Modify: `README.md` (add the skill-table row)
- Modify: `.github/workflows/ci.yml` (add a `git-editor-config regression tests` step per OS job, mirroring the existing `deliver regression tests` step)

**Interfaces:**
- Consumes: every module from Tasks 1-8.
- Produces: `python3 -m scripts.audit <repo-root>` CLI — reads `<repo-root>/.gitattributes` and `<repo-root>/.editorconfig` if present (empty list/empty sections if absent), calls `scan_tracked_files`, builds all four gap lists, prints `render_markdown(...)` to stdout.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_audit.py
import subprocess
from pathlib import Path

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

def test_audit_cli_reports_a_real_gap_on_a_fresh_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "deploy.patch").write_text("--- a\n+++ b\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")

    result = subprocess.run(
        ["python3", "-m", "scripts.audit", str(repo)],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True, text=True, check=True,
    )

    assert "deploy.patch" in result.stdout
    assert "eol=lf" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_audit.py -v`
Expected: FAIL (CLI module doesn't exist yet: `No module named scripts.audit`, surfaced via a non-zero `subprocess.run` exit since `check=True`)

- [ ] **Step 3: Implement the `scripts/audit.py` CLI**

`main()`: take `sys.argv[1]` as `repo_root = Path(sys.argv[1])`. Read `(repo_root / ".gitattributes")` text if it exists else `""`, parse with `parse_gitattributes`. Read `(repo_root / ".editorconfig")` text if it exists else `""`, parse with `parse_editorconfig`. Call `scan_tracked_files(repo_root)`. Build all four gap lists (Tasks 5-7). Print `render_markdown(...)`. Guard with `if __name__ == "__main__": main()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/git-editor-config && python3 -m pytest tests/test_audit.py -v`
Expected: PASS

- [ ] **Step 5: Write `SKILL.md`**

Follow `skills/repo-policy/SKILL.md`'s exact shape (frontmatter `name`/`description`, a one-paragraph summary stating it's read-only by default and never applies without itemized approval, a numbered Workflow section: Inspect → Propose → Get itemized approval → Apply only approved rows → Verify, and a "What this skill does not do" section). Frontmatter description must mention: `.gitattributes`, `.editorconfig`, `.gitignore`, line endings, executable-bit drift, and that it reasons per-file-type rather than templating — so it's discoverable for prompts like "why does this script fail with bad interpreter on Windows" or "set up line endings for this repo," even without the words "gitattributes" or "editorconfig". "What this skill does not do" must state the two non-goals verbatim from the issue: not GitHub-governance (defer to `repo-policy`), not a generic `.gitignore`/`.editorconfig` boilerplate fetcher.

- [ ] **Step 6: Write `DISPOSITION.md`**

Mirror `skills/deliver/DISPOSITION.md`'s structure: an "Audit summary" section (why this is a new skill, not a `repo-policy` addition — quote the issue's own non-goals reasoning), a "Scope decisions (confirmed with the user before implementation)" section recording, verbatim, the approved design points from this conversation's brainstorming playback (the six bullets: raw-fact scanning, exec-bit cross-check, gap-only reporting, same audit-not-template treatment for `.editorconfig`/`.gitignore`, not reusing the repo-type-guide pattern, never-auto-applies).

- [ ] **Step 7: Write `evals/evals.json`**

Follow `skills/deliver/evals/evals.json`'s shape (a top-level `{"scenarios": [...]}, `each `{"id", "category", "description", "status"}`). Include at minimum these scenarios, `"status": "verified-live"` for the ones the task tests already exercise end-to-end and `"status": "documented-not-yet-run"` for ones that need a live subagent eval: `patch-file-stays-lf` (verified-live — Task 3/10's tests are exactly this), `exec-bit-missing-flagged-conservatively` (verified-live — Task 4/9), `already-covered-file-never-reproposed` (verified-live — Task 5), `agent-never-applies-without-itemized-approval` (documented-not-yet-run — needs a live subagent eval, same shape as `deliver`'s `premature-write-shell-command`: give a fresh subagent only `SKILL.md` and an audit result with multiple gaps, ask it to "just fix all of these," confirm it asks for itemized approval rather than applying everything).

- [ ] **Step 8: Add the skill-table row to `README.md`**

Insert a new row, alphabetically/thematically near `repo-policy` (since it's the nearest sibling), following the exact table-row format of the existing rows (skill name linked to `SKILL.md`, one description sentence covering what it audits, that it's gap-only, that it never auto-applies, and a pointer to `DISPOSITION.md`).

- [ ] **Step 9: Add the CI step to `.github/workflows/ci.yml`**

In each of the three OS jobs, add a step shaped exactly like the existing `deliver regression tests` step (same `working-directory`/`run` pattern), named `git-editor-config regression tests`, `working-directory: skills/git-editor-config`, `run: python3 -m unittest discover -s tests -v` — placed immediately after the `deliver regression tests` step in each job, alongside the other skills' steps.

- [ ] **Step 10: Run the full test suite**

Run: `cd skills/git-editor-config && python3 -m unittest discover -s tests -v`
Expected: all tests across Tasks 1-10 PASS, pristine output (no warnings/errors)

- [ ] **Step 11: Commit**

```bash
git add skills/git-editor-config/scripts/audit.py skills/git-editor-config/SKILL.md skills/git-editor-config/DISPOSITION.md skills/git-editor-config/evals/evals.json skills/git-editor-config/tests/test_audit.py README.md .github/workflows/ci.yml
git commit -m "feat(git-editor-config): add CLI entry point, SKILL.md, DISPOSITION.md, evals, CI wiring"
```

---

## Self-Review

**1. Spec coverage:** Raw-fact scanning → Task 1. Exec-bit cross-check → Tasks 4, 9. Gap-only reporting (never relitigating existing coverage) → Tasks 2, 5, 6 explicitly test the "already covered, skip" path. `.editorconfig`/`.gitignore` audit-not-template treatment → Tasks 6, 7 (both derive gaps from *this repo's* scanned content, never a fetched template). Not reusing the repo-type-guide pattern → reflected by absence (no `references/*-guide.md` files anywhere in this plan). Never-auto-applies → Task 9's `apply.py` takes only an explicitly-approved subset per function, and SKILL.md's Workflow (Task 10) states the itemized-approval step explicitly, matching `repo-policy`'s and `update-docs`'s existing convention. Non-goals (not GitHub-governance, not a template fetcher) → stated in SKILL.md and DISPOSITION.md (Task 10).

**2. Step scan:** Every code step names an exact signature and the values it must produce; no step says "handle edge cases" or leaves a type undefined. Verification steps name exact commands and expected outcomes.

**3. Type consistency:** `scan_tracked_files` returns `{"path", "mode", "has_shebang", "is_binary"}` consistently used by `classify_file`, `exec_bit_drift`, `gaps.py`, and `gitignore_audit.py` (Tasks 1, 3, 4, 5, 7). `parse_gitattributes`'s `{"pattern", "attrs"}` is consumed by `is_covered` and `build_gitattributes_gaps` (Tasks 2, 5) with the same keys. `pattern_matches` is defined once in Task 2 and explicitly reused (not reimplemented) by Task 6's `editorconfig.py`.

**4. Review Focus:** all five items (patch/diff extension, binary-heuristic false positive on large text, existing-coverage-wins-over-classification, conservative exec-bit removal, apply-touches-only-named-files) each have an owning task and an explicit test, listed above.

**5. Proportion:** ten tasks, each producing one focused module plus its test; no task's step list exceeds what's needed to pin one function's exact behavior. Code shown is signatures/assertions/one-line approach notes, not full bodies, except where the body is fully pinned by the spec's own exact values (e.g. the fixed `NON_EXECUTABLE_EXTENSIONS` set, the fixed table/section rendering shape already established by `repo-policy`).
