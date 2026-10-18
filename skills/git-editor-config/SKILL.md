---
name: git-editor-config
description: Audit a repo's .gitattributes, .editorconfig, .gitignore, and tracked executable bits against what its actual file content (shebangs, binary signatures, patch files, mode bits) needs across multiple operating systems -- report the gaps as a Markdown matrix, and apply only the specific changes the user explicitly approves. Use this whenever the user hits a "bad interpreter" error after checkout, line-ending/CRLF-vs-LF problems, a script that lost its executable bit, or asks to set up or review line-ending/editor config for a repo worked on across Windows, WSL, Linux, or macOS -- even if they don't use the words "gitattributes" or "editorconfig".
---

Audit a repo's git-level and editor-level file-handling configuration against what its actual tracked content needs, report the gaps, and apply only what's explicitly approved. Read-only by default. Never applies anything without itemized approval -- there is no "apply everything" path anywhere in this skill.

This is reasoning about *this specific repo's* content, not a template: a `.gitattributes`/`.editorconfig`/`.gitignore` boilerplate for an ecosystem is a different, unrelated kind of tool (see "What this skill does not do").

## Workflow

### 1. Inspect (always read-only)

Run from this skill's directory (`skills/git-editor-config/`):

```bash
python3 -m scripts.audit <path to the local checkout>
```

This never mutates anything -- it only reads `.gitattributes`/`.editorconfig` if present and calls `git ls-files -s`/`git status`. It prints a Markdown report with one section per gap category (`.gitattributes gaps`, `Executable-bit drift`, `.editorconfig gaps`, `.gitignore gaps`), each omitted entirely when there's nothing to report in it. If every category is empty, it prints `No gaps found.`. Show the report to the user verbatim; it's the deliverable, not something to paraphrase away.

A file already covered by an existing `.gitattributes` rule or `.editorconfig` section is never re-proposed, even if this skill's own reasoning would have suggested something different for it -- existing, human-authored coverage always wins. That's what keeps this useful to re-run as a repo grows, instead of re-litigating settled decisions every time.

### 2. Propose

For each gap row, say in one line *why* that specific file needs that specific rule -- grounded in what was actually found (a shebang, a null byte, a `.patch` extension, a mode-bit mismatch), never a generic description. A gap with no clear signal is never in the report in the first place (`scripts/classify.py` returns no suggestion rather than guessing).

### 3. Get itemized approval

Ask which specific rows to apply. **Never offer or accept "apply everything."** If the user says "all of it," read back the specific rows and ask them to confirm by name.

### 4. Apply only the approved rows

Four functions in `scripts/apply.py`, one per category -- call only the one matching the approved row's category, with only the approved subset:

- `apply_gitattributes_rules(repo_root, approved)` -- appends one line per approved row to `.gitattributes`.
- `apply_exec_bit_fixes(repo_root, approved)` -- `git update-index --chmod=+x`/`--chmod=-x` for each approved row's exact path. This is a real git-tracked mode-bit change, not a filesystem-only `chmod` -- it's what actually ships to other checkouts.
- `apply_editorconfig_sections(repo_root, approved, default_settings)` -- appends one `[*.<ext>]` section per approved row to `.editorconfig`. There's no single "right" default per extension this skill can hardcode; ask the user what settings that extension should get (indent style/size, trailing whitespace, final newline) before calling this, the same way a human would decide it for that file type in that repo.
- `apply_gitignore_patterns(repo_root, approved)` -- appends one pattern per approved row to `.gitignore`.

### 5. Verify

Re-run `python3 -m scripts.audit`. Confirm the rows that were just applied no longer appear. Report the before/after explicitly.

## How the audit reasons, file by file

`scripts/scan.py` gathers raw, judgment-free facts per tracked file: git's own mode bits, whether the file starts with a shebang, and a binary-content signal (a null byte in the first chunk). `scripts/classify.py` turns that into a suggested `.gitattributes` rule, in this order: a `.patch`/`.diff` extension always suggests `text eol=lf -diff` (patch files must stay LF for `git apply` against an upstream tree); a binary signal suggests `-text -diff`; a shebang suggests `text eol=lf`; anything else gets no suggestion at all. `scripts/exec_bit.py` flags a missing `+x` on any shebang script, but only flags an *unexpected* `+x` for a fixed set of extensions that are unambiguously non-executable by convention (`.md .txt .json .yaml .yml .css .html`) -- deliberately conservative, since many repos legitimately ship executable `.py`/`.sh` files with no shebang.

## What this skill does not do

- Does not manage GitHub-level governance or repository settings (branch protection, CODEOWNERS, templates, Dependabot) -- that's `repo-policy`. This skill is project-level git/editor tooling config, a different concern.
- Does not fetch or generate a generic ecosystem `.gitignore`/`.editorconfig` boilerplate (e.g. "give me the Node.js gitignore"). Every suggestion here is grounded in this repo's own scanned content -- if nothing in the repo signals a need, nothing is suggested.
- Never applies a change the user didn't explicitly name. "Audit this repo" means read-only, always.
- Does not re-propose a file/pattern already covered by an existing rule, even to "fix" it to something this skill would have suggested instead -- an existing human decision is never silently second-guessed.
