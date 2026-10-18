# Repo type: generic

The fallback type. Use it when no other built-in type's detection
matches, and no repo or user override applies.

## Where docs live

`README.md` at the root, plus a `docs/` (or `doc/`, `guides/`) directory
if one exists. Treat any tracked Markdown/reStructuredText/AsciiDoc file
outside those as a doc too — don't assume a fixed layout.

## What's generated, and by what

No universal signal. Check each doc individually for a generated-file
marker (handled by `scripts/generated_docs.py`) before treating it as
hand-written. Common generators to recognize by name if mentioned:
Sphinx, MkDocs, Docusaurus, typedoc, JSDoc.

## What's public (must be documented)

Whatever the project's own README/CONTRIBUTING describes as its public
interface: exported functions in a library's top-level module, CLI
commands and flags, HTTP endpoints, config keys read from environment or
a config file.

## "Don't document" markers

None universal. Look for `@internal`, `@private`, a leading underscore
naming convention, or an explicit "internal only" note in the source.

## Breaking vs. routine for docs purposes

A rename, removal, or changed default for anything in "what's public"
above is breaking — the doc describing it is now wrong, not just stale.
