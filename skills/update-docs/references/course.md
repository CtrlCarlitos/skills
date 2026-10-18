# Repo type: course

There's no reliable file signature for a course repo. Select it
explicitly -- via this repo's `.update-docs/type.md` override or your own
`~/.config/update-docs/types/course.md` -- rather than relying on
detection.

## Where docs live

Lesson/module files themselves (often numbered, e.g. `01-intro.md`), a
syllabus or outline page, and per-lesson exercise/starter-code READMEs.

## What's generated, and by what

Rarely anything -- course content is usually hand-authored. An
exception: an auto-generated table of contents or a syllabus assembled
from per-lesson front-matter by a build script, which should say so.

## What's public (must be documented)

Every lesson's prerequisites and learning objectives, since those are
what a learner checks before starting. Exercise instructions and
expected outcomes.

## "Don't document" markers

Instructor-only notes (often in a separate `instructor/` directory or a
file explicitly marked "do not share with learners") are out of scope
for a learner-facing audit.

## Breaking vs. routine for docs purposes

A renumbered or reordered module, a changed prerequisite, or a removed
exercise/dataset a lesson depends on is breaking -- it invalidates links
and expectations learners already have from prior cohorts' materials.
