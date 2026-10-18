# `git-editor-config`: audit and scope decisions

For CtrlCarlitos/skills#18.

## Audit summary

The issue is explicit that this is not a one-shot template task: the right `.gitattributes`/`.editorconfig`/`.gitignore`/executable-bit configuration depends on a repo's actual file types and tooling, and needs revisiting as the repo grows. It cites this repo's own history as the concrete precedent -- in #9, `.gitattributes` was hand-tuned per file type (`* text=auto eol=lf`, `*.sh text eol=lf`, `*.patch text eol=lf -diff` specifically), and a separate fix (switching away from a GNU-only `diff` flag in the sync script) surfaced a pre-existing bug where 7 vendored scripts had silently lost their executable bit relative to upstream -- a mode-bit regression the existing tooling couldn't even see, because nothing was checking file modes at all.

This is explicitly **not** `repo-policy` territory: `repo-policy` (#5/#17) covers GitHub-level governance (branch protection, CODEOWNERS, templates, Dependabot) -- a different kind of concern from project-level git/editor tooling config that has nothing to do with GitHub. Kept as a separate skill per the issue's own non-goals.

## Scope decisions (confirmed with the user before implementation)

Recorded verbatim from this conversation's brainstorming playback, approved before any code was written:

1. **Audit tracked files by extension, by shebang line, and by git's actual mode bits** (`git ls-files -s`), classifying each into: text needing `eol=lf`/`eol=crlf`, binary/generated needing `-text -diff`, or already-covered by an existing `.gitattributes` pattern.
2. **Cross-check executable bits against shebang presence** (a script without `+x`, or a non-script with it) -- reusing the exact bug class this repo's own #9 history hit.
3. **Report only gaps relative to the repo's existing `.gitattributes` coverage**, not already-settled rules, so the audit stays useful as the repo grows (the issue's explicit "iterate over time" requirement) -- never relitigating a file already covered, even if this skill's own reasoning disagrees with the existing rule.
4. **`.editorconfig` and `.gitignore` get the same audit-not-template treatment**: `.editorconfig` gaps are uncovered file extensions actually present in the repo, one row per extension (not per file); `.gitignore` gaps are tracked-but-probably-generated files or untracked-but-unignored files that look generated, from the repo's own scanned state -- never a fetched ecosystem boilerplate.
5. **Does not reuse `update-docs`/`release-notes`' repo-type-guide pattern** (generic/odoo/phoenix/go/...). That pattern exists for documentation *conventions* that differ by ecosystem; this skill's reasoning is about actual scanned file content (shebangs, patch files, binary signatures), which isn't ecosystem-specific in the same way.
6. **Never auto-applies.** Proposes additions/changes with per-file-type reasoning; applies only on itemized, explicit approval -- same convention `repo-policy` and `update-docs` already established in this repo.

Non-goals, from the issue directly: not a GitHub-governance tool (`repo-policy`'s territory); not a generic `.gitignore`/`.editorconfig` template generator.

## What `references/` covers

Nothing yet -- v1 needed no reference material beyond `SKILL.md` itself (no policy-lookup chain, no repo-type guides; see scope decision 5 above for why). If a future need for one arises (e.g. a catalog of common shebang interpreters, or known binary file signatures beyond the null-byte heuristic), it belongs here.
