# Getting started with study-coach

This walks you through using `study-coach` for real, start to finish: asking Claude Code to build a learning bundle for your child, opening what it produces, actually taking the exam and reviewing the flashcards, and bringing the results back so progress is tracked over time.

By the end, you'll have a real set of files on your own computer -- an exam page, a flashcard deck, and a small dashboard -- that you can open in any browser, no internet connection or server required.

## What study-coach actually delivers

For one child, on one subject/topic, `study-coach` produces:

- **An exam** (`exam.html`) -- a self-contained web page with a mix of question types (multiple choice, true/false, fill-in-the-blank, matching, and open-response), which grades itself the moment your child clicks "download results," except for open-response questions, which you or Claude read and grade by hand afterward.
- **A flashcard deck** (`flashcards.html`) -- tap or click a card to flip it and reveal the answer, mark "Got it" or "Missed it," and watch a simple points/streak counter as you go. Cards your child keeps missing come back more often in later decks.
- **A practice version of the exam** (`practice.html`, optional) -- the same questions, same format, but it never produces a results file and shows a "Práctica: esto no cuenta" ("Practice: this doesn't count") banner. It's there so your child can rehearse the exam's format as many times as they want before the real one, with zero risk of a rehearsal attempt accidentally being recorded as a real result.
- **A per-topic index page** (`index.html`, inside that topic's own folder) linking whichever of the three above actually exist for that topic.
- **A family dashboard** (`index.html` at the root of your workspace -- a different file from the one above, see "Two different index.html files" below) showing, per child and subject, how each exam went over time and which topics still need work.

Every piece of content -- the actual exam questions, the flashcard prompts and answers -- is grounded against a real source before it's written: El Salvador's official MINEDUCYT curriculum where it exists for that subject and grade, your family's own Santillana textbook (from a photo you supply) where MINEDUCYT doesn't cover it, or general reliable sources for a topic that isn't a school subject at all. `study-coach` will tell you, not guess, when neither source covers something.

**Not included yet:** video, a printable version of the flashcards, and anything fancier than "a card missed before comes back a bit more often" for spaced repetition. All three are deliberate, documented choices to keep the first version simple -- see `DISPOSITION.md` if you're curious why.

## Before you start: set up your family's workspace

`study-coach`'s code lives in this repository, but your family's actual data -- your kids' names, grades, exam history, and any textbook photos you supply -- never should. This repo is public on GitHub, so point `study-coach` at a folder *outside* it, like a folder in your own home directory:

```text
~/study-coach-family/
```

You don't need to create this folder by hand or run any command yourself -- just tell Claude Code where you want it the first time you ask for something, and it will set up the folder structure for you. You only need to remember the path and reuse it every time, so everything accumulates in one place instead of starting over.

## Step 1: Ask Claude Code to build a learning bundle

Open a Claude Code session in this repository (or anywhere `study-coach` is installed) and describe what you need in plain language. For example:

> My son Mateo is in 4th grade in El Salvador and he's really struggling with sustantivos (nouns) in Lenguaje. Can you build him an exam and some flashcards, grounded in what he's actually taught? Use `~/study-coach-family` as the workspace.

Claude will:

1. Check whether El Salvador's MINEDUCYT curriculum actually covers Lenguaje for 4th grade. As of this writing, it confirmed does not (MINEDUCYT's materials cover Matemática grades 2-3, but not Lenguaje for grades 3-5) -- this is a real, confirmed gap, not a hypothetical one.
2. Because of that gap, Claude will ask you for a photo of the relevant page(s) from Mateo's Santillana textbook -- the book his school actually requires -- instead of inventing material from scratch. Send it a photo (even a phone snapshot of the page is fine) and it will use that as the source going forward, keeping it for next time too.
3. Write real exam questions and flashcards about sustantivos, grounded in whichever source actually covered it, and tell you explicitly which source backed the material.
4. Save everything under `~/study-coach-family/children/mateo/subjects/lenguaje/sustantivos/` and tell you the exact paths.

If MINEDUCYT *had* covered the topic, Claude would have used that directly and skipped asking for a photo -- the photo step only happens for a real, confirmed gap, never as a default.

## Step 2: Open and take the exam

Open `exam.html` from the folder Claude gave you, in any web browser -- double-clicking the file works, no server needed. Have Mateo answer the questions normally. When he's done, click **"Descargar resultados"** ("Download results"). This saves a small results file (something like `exam1-results.json`) to your Downloads folder.

Nothing is saved automatically before that click -- the page is a self-contained file with no server behind it, so if the browser is closed or the page is reloaded without downloading, the answers given so far are simply gone and Mateo would need to retake it from the start. The download step is the only way any of his answers leave the page.

Bring that file back to Claude in your next message -- just say where it is. Claude will:

- Recompute every answer's correctness itself (it never trusts the page's own on-screen grading, which is just a convenience check for the page -- the real scoring always happens from scratch on the raw answers).
- For any open-response question, read what Mateo wrote and grade it based on judgment, since there's no way for a static page to grade free-text writing on its own.
- Tell you which topics he's solid on and which need more work -- a real breakdown, not just a score out of 20.
- Update the family dashboard (the workspace-root `index.html` -- see below) so this exam shows up in Mateo's history from now on.

If Claude also built `practice.html` for you, open that first, as many times as you like, before the real exam -- it shows an on-page score summary immediately (no download needed) and there is nothing in that page that could ever be brought back and mistaken for a real result. Note that `practice.html` is always generated *alongside* `exam.html`, from the same questions, not instead of it -- the real exam file still exists in the folder the whole time. You're simply free to not open it until Mateo is actually ready for it to count.

## Step 3: Review the flashcards

Open `flashcards.html` the same way. Click or tap a card to flip it and see the answer underneath; use "La sé" ("Got it") or "No la sé" ("Missed it") to mark each one. When finished, click **"Descargar resultados"** again and bring that file back to Claude the same way.

Claude will record that review session (every session is kept, even repeats of the same deck on different days, since each one is a real study session) and the *next* deck it builds for this topic will include extra copies of whichever cards Mateo keeps missing, so those come up more often without you having to ask for it specifically.

## Step 4: The quick-answer shortcut

Not every question needs a full bundle. If Mateo gets stuck on one specific thing, just ask directly:

> Mateo's asking what a "sustantivo propio" is -- can you ground an answer against his actual textbook, not just a generic explanation?

For a request like this, Claude defaults to a small flashcard deck (typically 1-3 cards) answering just that question -- grounded the same careful way, but without committing to a full exam over it.

## Two different `index.html` files

It's easy to confuse these, so to be explicit:

- `~/study-coach-family/children/mateo/subjects/lenguaje/sustantivos/index.html` -- a landing page for *this one topic*, linking its own exam/flashcards/practice page. This gets rewritten every time that topic's bundle is regenerated, and only ever reflects whatever files currently exist for that topic.
- `~/study-coach-family/index.html` -- the **family dashboard**, one level up at the very root of your workspace. This is the one that accumulates: every exam any child has ever taken, with the per-topic breakdown, stays in this view over time. Open this one when you want the overall picture, not just one topic's.

## Testing the pipeline yourself, without a Claude conversation

If you want to verify the underlying mechanics work on your own machine -- for example, right after installing this repo, before trusting it with your actual family's data -- `study-coach` ships three small developer command-line tools that exercise the pipeline directly. These are not meant for day-to-day use (a real bundle's content has to come from an actual grounded conversation with Claude), but they're useful for a sanity check:

```bash
cd skills/study-coach

# Check what sources ground_topic finds (or doesn't) for a subject/topic/grade
python3 -m scripts.audit_grounding <workspace> <subject> <topic> <grade> [--general] [--photo <path>]

# Render a hand-written exam.json to a real exam page, or score a results file against it
python3 -m scripts.audit_exam render <exam.json> <out.html>
python3 -m scripts.audit_exam score <exam.json> <results.json> <workspace> <child_id> <taken_at> [--grades <grades.json>]

# Build a full bundle (exam + flashcards, optionally practice) from hand-written exam.json/deck.json files
python3 -m scripts.audit_bundle build <workspace> <child_id> <exam.json> <deck.json> [--practice]

# Record a flashcard results export by hand
python3 -m scripts.audit_bundle record <workspace> <child_id> <deck.json> <results.json> <reviewed_at>
```

These require you to supply your own `exam.json`/`deck.json` files by hand (see `tests/test_audit_exam.py` and `tests/test_audit_bundle.py` in this skill's folder for real, working examples of that file shape) -- they don't generate question content themselves, since that's always Claude's job when grounding a real topic.

## If something looks wrong

If an exam or flashcard set doesn't match what your child's teacher actually taught, that's the single most important kind of problem to report -- the whole point of the grounding step is to prevent exactly that. Tell Claude which source it cited (every generated page's material is traceable back to a specific source) and where it diverges from what the school teaches, so the mismatch can be tracked down.
