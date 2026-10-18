# Repo type: course

There's no reliable file signature for a course repo (it's usually just
Markdown, slides, or notebooks). Select it explicitly — via this repo's
`.release-notes/` override or your own `~/.config/release-notes/types/
course.md` — rather than relying on detection.

## Detection

None. Set explicitly in a repo or user override.

## Breaking

- A renamed or reordered module/lesson that changes the URL, slug, or
  numbering learners or links depend on.
- A changed prerequisite (a lesson now assumes material that moved or
  was removed).
- A removed exercise, dataset, or starter repo a lesson depends on.

## Security

Rarely applicable. If the course ships runnable code or infrastructure
(a sandbox, a CI template, credentials handling guidance), treat a fix to
that the same as a generic security fix.

## Upgrade notes

- A changed required tool version (language runtime, IDE, dependency)
  learners must install before continuing.
- A changed submission or grading process.

## Examples

- Added: "New lesson: 'Error handling patterns' (#12, 4d5e6f7)."
- Changed: "Reworked the 'Intro to functions' lesson with new examples
  (#15, 8a9b0c1)."
- Breaking: "Renumbered modules 4–6; links to the old numbers in prior
  cohort materials will 404 (#18, 2b3c4d5)."
- Fixed: "Corrected the sample output in the 'Recursion' exercise, which
  didn't match the starter code (#20, 6e7f8a9)."
