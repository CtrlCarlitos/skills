# `study-coach`: audit and scope decisions

For the user's own kids (El Salvador, grades ~3rd-5th). This is Plan 1 of 3 for the spec's "study-coach v1" (+1 video plan, deferred to its own later issue). Full design: `docs/superpowers/specs/2026-10-18-study-coach-design.md`.

## Audit summary

Why a new skill, not an extension of the existing `teach` skill (`~/.claude/skills/teach/`, read directly before this design was written): `teach` is built for one curious adult, self-directed, over a long-running single-topic workspace, producing HTML lesson pages with lightweight in-lesson quizzes -- no video, no audio, no flashcards, no gamification, no exam generation, no curriculum/ministry-standard alignment, nothing kid-specific. `study-coach` is a different shape of problem: a parent generates a full multi-artifact bundle *for* a child who never operates the tool directly, grounded against an external, country-specific curriculum standard, with a confidence-building design goal `teach` has no equivalent of. `study-coach` does reuse `teach`'s core philosophy where it actually applies -- ground in cited, high-trust sources, never recite parametric/memorized knowledge as if it were verified -- see the Grounding strategy below.

## Scope decisions (confirmed with the user before implementation)

Recorded verbatim from the design doc's "Decided" section, settled before this plan was written:

1. **Two entry points, one engine** (not yet built in this plan): *full bundle* (subject + topic in -> video + flashcards + exam + post-exam gap report) and *quick answer* (one stuck question in -> a smaller artifact). Both parent-initiated; the kid never operates Claude Code or any CLI.
2. **Dual grounding strategy, implemented in this plan:** a curricular topic grounds against MINEDUCYT where it has real coverage for that grade/subject, falls back to the family's own Santillana photos where MINEDUCYT's coverage has gaps (confirmed real for Lenguaje grades 3-5), and states explicitly which source backed which part -- never silently blending an ungrounded claim in. A non-curricular topic grounds against general sources instead, same "cite it, don't just recite it" discipline.
3. **Multi-child-aware workspace, implemented in this plan:** each kid gets their own partition under the family's home workspace -- not a shared pool that would conflate one kid's results with another's.
4. **Workspace lives outside this repo by default, implemented in this plan:** `CtrlCarlitos/skills` is a public GitHub repo (confirmed via `gh repo view`); the family's real data (kids' names, grades, exam history, Santillana photos) must never live inside it. Every function in this plan takes an explicit `workspace: Path` argument -- nothing hardcodes or assumes a path inside `skills/study-coach/`.
5. **Santillana ingestion is ad hoc and accumulating, implemented in this plan:** the parent supplies a photo only when a specific topic actually needs it, not a one-time bulk scan. A second photo for the same subject/topic adds to the cache, never overwrites the first.
6. **Exam question types and grading split** (not yet built in this plan, recorded here so the next plan's reader has full context): multiple choice, single-select, fill-in-the-blank, true/false, and matching all self-grade client-side in static HTML; open/free response cannot self-grade without a backend, so it's folded into the already-settled "parent brings results back to the next invocation" flow used for persistence in general.
7. **State persistence despite "no backend":** a static exam/flashcard page cannot silently write back to the workspace. The exam (once built) will produce a results export the parent brings back into the next invocation -- that's the point at which the persisted report and dashboard actually update. Not yet exercised by this plan's code (no exam exists yet), but the workspace layout this plan ships does not preclude it.

Non-goals, from the design doc directly: no mobile app, no multi-family/teacher platform, no paid TTS, no other country's curriculum, no general-purpose spaced-repetition engine unless a simpler mechanic proves insufficient.

## What `references/` covers

Nothing yet -- this plan needed no reference material beyond `SKILL.md` and the spec itself (no policy-lookup chain, no repo-type guides). If a future plan needs one (e.g. the exam question-type taxonomy, or the topic-tagging/competency structure), it belongs here.
