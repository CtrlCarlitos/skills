# Classifying a page by Diátaxis type

Generate mode places a new page by type, following [Diátaxis]
(https://diataxis.fr). Four types, each answering a different question
a reader has -- use the concrete signs below, not just the name, to
classify a gap or an existing page.

## Tutorial

**Question it answers:** "Can you teach me, by doing something real?"

**Signs:** Second person, imperative steps in a fixed order ("Create a
file named...", "Run..."), a single concrete worked example from zero to
a working result, no branching ("if you want X instead, see..."). Ends
with the learner having built or run something, not just read about it.

**Lives under:** `tutorials/`, or a "Getting started" / "Quickstart"
page.

## How-to guide

**Question it answers:** "How do I accomplish this specific task?"

**Signs:** Assumes the reader already knows the basics (unlike a
tutorial). States the goal up front, then the shortest path to it. May
branch ("if using Postgres... if using MySQL..."). Doesn't re-explain
concepts the reference/explanation docs already cover.

**Lives under:** `how-to/`, `guides/`, or a task-named page
("Configuring X", "Deploying to Y").

## Reference

**Question it answers:** "What exactly does X take, return, or mean?"

**Signs:** Structured by the shape of the thing described (every
parameter, every flag, every field), not by a narrative. Accurate and
complete over explanatory -- a reader looks something up here, doesn't
read it start to end. Often generated or semi-generated from source
(docstrings, `--help` output, OpenAPI).

**Lives under:** `reference/`, `api/`, or wherever the repo type's own
convention generates reference docs to.

## Explanation

**Question it answers:** "Why does it work this way?"

**Signs:** Discusses trade-offs, alternatives considered, context and
history. No steps to follow, no exhaustive parameter list -- it's
background a reader consults to understand, not to act.

**Lives under:** `explanation/`, `concepts/`, `design/`, or an
"Architecture"/"Why" page.

## When a page mixes types

A page that's half-tutorial, half-reference is a common real-world
smell: a "Getting started" page that trails off into an exhaustive
config reference partway through. Flag this as a finding (it should
probably split into two pages) rather than trying to force it into one
category.

## Using this for Generate mode

Before writing a new page, name which of the four it is and why, using
the signs above -- not just "this seems like a guide." If a repo already
has a `docs/` structure with existing type-named directories, match that
structure instead of introducing new ones.
