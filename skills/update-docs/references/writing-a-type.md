# Writing your own repo type

The rules this skill applies are the same for every repo: code is the
source of truth, scope to the change, keep edits minimal, generated docs
go through their generator, never invent, run the repo's own checks,
report what was left alone. What changes per repo type is only where
docs live, what's generated and by which command, what counts as the
public surface that must be documented, and what "don't document"
markers to respect.

A built-in type (`generic.md`, `odoo.md`, `phoenix.md`, `go.md`,
`flutter.md`, `course.md`, `docs.md` in this directory) is the documented
starting point -- copy whichever is closest and edit it.

## Where to put it

Looked up in this order, first match wins (same convention as
`release-notes`' repo types):

1. **Repo override:** `.update-docs/type.md` in the repo being audited.
   Committed, so everyone working on that repo gets the same type. This
   file *replaces* the built-in lookup entirely.
2. **User config:** `~/.config/update-docs/types/<name>.md`, for a
   personal type reused across repos you work on.
3. **Built in:** the files in this directory.

A repo can also use `.update-docs/` to set its style guide and which
docs it considers authoritative (e.g. "README.md is the source of truth
for CLI flags, not docs/cli.md" when both exist and might disagree).

## Required sections

Use the same headings as a built-in file, in this order:

- `## Where docs live` -- the actual file/directory convention for this
  ecosystem, not a generic restatement.
- `## What's generated, and by what` -- the specific generator command
  (`go doc`, `mix docs`, `dart doc`, `oca-gen-addon-readme`, a site
  builder) and its output location, so a generated file is never
  hand-edited.
- `## What's public (must be documented)` -- the concrete signal (an
  exported identifier, a `@moduledoc` without `false`, a model without a
  `_` prefix) that marks something as the documented surface.
- `## "Don't document" markers` -- the inverse: what explicitly opts out.
- `## Breaking vs. routine for docs purposes` -- what change to the
  public surface makes an existing doc wrong (not just stale), so it's
  triaged correctly.

## Keep it specific, not generic

A good type file names actual file paths, tool commands, and language
conventions (`@moduledoc false`, `ir.model.access.csv`,
`AndroidManifest.xml`) rather than restating the generic rules in
different words. If a section would just repeat `generic.md`, leave it
out.
