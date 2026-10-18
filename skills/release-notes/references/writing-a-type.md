# Writing your own repo type

The rules this skill applies are the same for every repo: resolve a
range, build grounded entries, read the diff instead of trusting commit
labels, match existing conventions, never invent claims, draft only. What
changes per repo type is only what counts as breaking, security-relevant,
or an upgrade step for that kind of project.

A built-in type (`generic.md`, `odoo.md`, `phoenix.md`, `go.md`,
`flutter.md`, `course.md`, `docs.md` in this directory) is the documented
starting point — copy whichever is closest and edit it.

## Where to put it

Looked up in this order, first match wins:

1. **Repo override:** `.release-notes/type.md` in the repo being
   described. Committed, so everyone working on that repo gets the same
   type. This file *replaces* the built-in lookup entirely — it doesn't
   need to follow the detection convention below, since the repo is
   naming it explicitly.
2. **User config:** `~/.config/release-notes/types/<name>.md`, for a
   personal type reused across repos you work on. Pick `<name>` to match
   what you'll pass to the skill (or what `detect_type` would already
   return, if you want it picked automatically).
3. **Built in:** the files in this directory.

## Required sections

Use the same headings as a built-in file, in this order, so the skill
and a human reader both know where to look:

- `## Detection` — the file or content signature that identifies this
  repo type (omit/say "None" if it can't be reliably detected, like
  `course` and `docs` — those are always selected explicitly).
- `## Breaking` — what counts as a breaking change for this kind of
  project, beyond the generic cases (removed public API, changed
  default, incompatible format).
- `## Security` — what counts as security-relevant here specifically
  (access rules, permission manifests, auth middleware, etc.) — not just
  "there was a CVE."
- `## Upgrade notes` — what a reader must *do*, not just know: run a
  migration, set an env var, bump a toolchain version.
- `## Examples` — two or three realistic entries in this skill's entry
  shape (ends with `(#PR, sha)`), so the agent has a concrete pattern to
  match, not just a description.

## Keep it specific, not generic

A good type file names the actual file paths, config keys, or
conventions of that ecosystem (`migrations/<version>/`,
`priv/repo/migrations/`, `AndroidManifest.xml`) rather than restating the
generic rules in different words. If a section would just repeat
`generic.md`, leave it out — the skill already applies the generic rules
everywhere; a type file only needs to add what's different.
