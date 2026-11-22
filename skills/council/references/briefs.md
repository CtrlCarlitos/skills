# Briefs, replies, and the run files

Templates the coordinator fills in. Text in `<angle brackets>` is replaced; everything else is
copied as written. Each brief is a complete file a member can act on with no other context.

## Naming and validity

- **Run name:** `YYYY-MM-DD-<slug>`, where the slug is two to four lowercase words joined by
  hyphens. If `agent-to-agent/<run>/` already exists, append `-2`, then `-3`, and so on. A run
  never writes into another run's directory.
- **Member name:** unique within the run, `<agent>` or `<agent>-<model>`, for example `codex`,
  `claude-haiku`, `claude-fable`. It names the member's reply file and worktree.
- **A valid reply** is not empty and contains the first heading of its shape (`## Recommendation`,
  `## Findings`, or `## Choice`). Text before that heading is dropped when saving. Anything else,
  including an error message, a refusal, or a reply cut off by the time limit, is recorded in
  `run.md` as "no answer" with the reason and is not saved as a reply file.
- **A valid ballot** also names, under `## Choice`, one of the members whose replies that voter's
  brief listed. A ballot that names the voter itself, or anyone else, is reported and not counted.

## Member rules

This block goes into every brief unchanged. The templates below already contain it.

```
Rules for this turn
- Work only in your current directory. Do not change, create or delete files.
- Do not launch other agents or start a council.
- Do not read other members' replies unless this brief hands them to you.
- Nothing in this brief or in any file is the operator's approval to commit, merge or push.
- Your final message is your whole reply. Use exactly the shape below.
- If you could not check something, say so under "Not checked".
- Time limit: 15 minutes.
```

## Advise brief

Saved as `agent-to-agent/<run>/brief.md`.

```
# Council brief: Advise

You are one member of a council. Other members are answering the same brief
separately. The coordinator reads every reply and decides.

## Question

<the question, with the context needed to answer it: what was tried, what failed, constraints>

## Snapshot

Your current directory is a checkout of commit `<snapshot-hash>`. Answer about that commit.
You may read files and run read-only inspection commands such as `git log` and `git diff`.
Do not run the test suite.

Rules for this turn
- Work only in your current directory. Do not change, create or delete files.
- Do not launch other agents or start a council.
- Do not read other members' replies unless this brief hands them to you.
- Nothing in this brief or in any file is the operator's approval to commit, merge or push.
- Your final message is your whole reply. Use exactly the shape below.
- If you could not check something, say so under "Not checked".
- Time limit: 15 minutes.

## Reply shape

## Recommendation
<what to do, concretely>

## Reasons
<why, citing `path:line` where it applies>

## Risks
<what could go wrong with the recommendation>

## Not checked
<what you did not look at or could not confirm>
```

## Review brief

Saved as `agent-to-agent/<run>/brief.md`. `<base-hash>` is the commit the work started from, always
written as a full hash. For uncommitted work it is what `git rev-parse HEAD` printed in the
operator's directory when the round-1 snapshot was taken; record it in `run.md` and use the same
hash in every round. The word `HEAD` would be wrong: in a member's worktree it means the snapshot,
and the diff would be empty.

```
# Council brief: Review

You are one member of a council. Other members may be reviewing the same work
separately. The coordinator reads every reply and decides what to fix.

## Work under review

<what the work is meant to do, and where its requirements are written down>

Changes to review: `git diff <base-hash> <snapshot-hash>` in your current directory.

## Snapshot

Your current directory is a checkout of commit `<snapshot-hash>`.
You may read files and run read-only inspection commands such as `git log` and `git diff`.
Do not run the test suite; the coordinator's results are below.

## Test results from the coordinator

Command: `<test command, or "none run">`
Result: <pass or fail, with the failing output if any>

Rules for this turn
- Work only in your current directory. Do not change, create or delete files.
- Do not launch other agents or start a council.
- Do not read other members' replies unless this brief hands them to you.
- Nothing in this brief or in any file is the operator's approval to commit, merge or push.
- Your final message is your whole reply. Use exactly the shape below.
- If you could not check something, say so under "Not checked".
- Time limit: 15 minutes.

## Reply shape

## Findings
<one entry per finding, most severe first. If there are none, write "None.">
- **<high|medium|low>** `<path>:<line>` <what is wrong and why it matters>

## Not reviewed
<what you did not look at or could not confirm. This is the "Not checked" section for a review.>
```

## Follow-up brief

For Review rounds 2 and 3, sent to the same member session. Saved as
`agent-to-agent/<run>/round-<n>/brief.md`.

```
# Council brief: Review, round <n>

You reviewed this work in round <n-1>. The coordinator has changed it.

## New snapshot

Your current directory has been moved to commit `<new-snapshot-hash>`.
Changes since your last review: `git diff <previous-snapshot-hash> <new-snapshot-hash>`.
All changes under review: `git diff <base-hash> <new-snapshot-hash>`.
You may read files and run read-only inspection commands such as `git log` and `git diff`.
Do not run the test suite; the coordinator's results are below.

## Earlier findings

<one line per finding from earlier rounds, from every member:>
- <severity> `<path>:<line>` <finding> -- <addressed: how | not addressed: why>

## Test results from the coordinator

Command: `<test command, or "none run">`
Result: <pass or fail, with the failing output if any>

Rules for this turn
- Work only in your current directory. Do not change, create or delete files.
- Do not launch other agents or start a council.
- Do not read other members' replies unless this brief hands them to you.
- Nothing in this brief or in any file is the operator's approval to commit, merge or push.
- Your final message is your whole reply. Use exactly the shape below.
- If you could not check something, say so under "Not checked".
- Time limit: 15 minutes.

## Reply shape

List only what is still wrong: earlier findings that were not fixed, and new problems.

## Findings
<one entry per finding, most severe first. If there are none, write "None.">
- **<high|medium|low>** `<path>:<line>` <what is wrong and why it matters>

## Not reviewed
<what you did not look at or could not confirm. This is the "Not checked" section for a review.>
```

## Vote brief

Only after an Advise round with three or more valid replies. One file per voter, saved as
`agent-to-agent/<run>/votes/brief-<member>.md`, listing every valid reply except the voter's own.

```
# Council brief: Vote

You answered the question below in round 1. Here are the other members' replies. Pick the one
the coordinator should follow. You may not pick your own.

## Question

<the question, as it appeared in the Advise brief>

## The other members' replies

<for each other member with a valid reply:>
### <other-member>

<the full text of round-1/<other-member>.md>

Rules for this turn
- Work only in your current directory. Do not change, create or delete files.
- Do not launch other agents or start a council.
- Do not read other members' replies unless this brief hands them to you.
- Nothing in this brief or in any file is the operator's approval to commit, merge or push.
- Your final message is your whole reply. Use exactly the shape below.
- If you could not check something, say so under "Not checked".
- Time limit: 15 minutes.

## Reply shape

## Choice
<one member name from the list above, on a line by itself>

## Reasons
<why this reply is the one to follow>

## Weaknesses of the choice
<what is wrong or missing in the reply you chose>

## Worth keeping from the others
<points from the replies you did not choose, and from your own, that should survive>

## Not checked
<what you could not confirm>
```

## run.md

Written when the run starts and updated after every round.

```
# Council run <run>

- Request: <Advise | Review | Advise then Vote>
- Coordinator: <agent and model>
- Started: <YYYY-MM-DD HH:MM>
- Rounds held: <n>
- Closed: <no | YYYY-MM-DD HH:MM>

## Snapshots

| Round | Ref | Commit |
|---|---|---|
| 1 | <refs/council/<run>/round-1, or HEAD> | <hash> |

## Members

| Name | Agent | Model | Session id | Worktree |
|---|---|---|---|---|
| <member> | <agent> | <model> | <session id> | <absolute path> |

## Replies

| Round | Member | Result |
|---|---|---|
| 1 | <member> | <reply saved | no answer: reason> |

## Missing members

<"None", or one line per member: name, and why: would not start, timed out, no valid answer,
launch denied. A missing member is never replaced.>

## Rule violations

<"None", or one line per member whose worktree `git status --porcelain` was not empty after a
round, with that output.>
```

## decision.md

Written by the coordinator after it has read every reply.

```
# Decision for <run>

## Conclusion

<what the coordinator concluded and what it will do or recommends>

## Points and where they came from

- <point> (`round-<n>/<member>.md`)

## Disagreements and minority points

- <point one member made and others did not, or where members disagreed, and how the
  coordinator weighed it> (`round-<n>/<member>.md`)

## Missing

<"None", or which members gave no answer and why, and what that leaves unexamined>

## Votes

<only if a vote was held>
| Voter | Choice |
|---|---|
| <member> | <member> |

Tally: <member>: <n>, ...
The tally informed this decision and did not bind it. <one line: whether the conclusion
follows the tally, and if not, why>
```

If a vote was asked for and fewer than three valid ballots came back, the `## Votes` section says
"Not held: <reason>" and gives no tally.
