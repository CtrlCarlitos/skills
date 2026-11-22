# Council: a coordinator whose command tool is PowerShell

Date: 2026-11-22. Size: a small change to an existing skill. Status: awaiting operator approval.

## Intent

Codex and Agy on Windows have one command tool, and it runs PowerShell. The council skill's
commands are bash, so both stopped at the shell check (issue #51). The operator wants both to be
able to coordinate a council on Windows.

## Goals, non-goals, anti-goals

- **Goal:** a coordinator with only PowerShell can run every council command, with the same time
  limit, alias protection and snapshot behaviour as a bash coordinator.
- **Non-goal:** `cmd`. Members' shells (members need none). Fixing Codex's other blockers on
  Windows, which are outside the skill: the guardrail hook that refuses every command
  (agent-guardrails#685) and a sandbox that may keep `.git` read-only.
- **Anti-goal:** a second, translated set of commands that can drift from the first. A helper
  script in `skills/council/`. A launch that silently loses the time limit or picks up an alias.

## Approaches

- **A. Call Git Bash from PowerShell (chosen by the operator).** Each council command is passed,
  unchanged, to Git for Windows' `bash.exe`. One command set, already run in CI on Windows.
  Depends on Git for Windows, which `git` needs anyway.
- **B. Native PowerShell commands.** No Git Bash dependency, but the time limit and alias
  protection would be rebuilt in PowerShell and verified per agent, and two command sets kept in
  step. Rejected for that.

## Design

1. **Shell check gains a third outcome.** Today: bash or zsh, else stop. New: with only
   PowerShell, find Git Bash and continue; stop only if there is none (or the tool is `cmd`).
2. **Finding Git Bash, once per run.** `(Get-Command git).Source` prints `...\Git\cmd\git.exe`;
   Git Bash is `...\Git\bin\bash.exe` beside it. `C:\Windows\System32\bash.exe` is WSL's launcher
   and is never used. Confirm with one wrapped command that prints the bash version and
   `uname -s` (expect `MINGW` or `MSYS`). The coordinator then writes that literal path in every
   command.
3. **The wrapper.** Every command in the skill is run as:

   ```
   & 'C:\Program Files\Git\bin\bash.exe' -c '<the bash command, unchanged>'
   ```

   - The whole bash command is one PowerShell single-quoted string, so PowerShell expands nothing
     in it (`$`, backticks).
   - Inside it, quote with single quotes only, each written twice (`''`). No double quote appears
     anywhere, which avoids PowerShell's known trouble passing double quotes to native programs.
     So the fixed prompt is written `''Read the brief at agent-to-agent/brief.md and follow it.''`
     and a path with a space is `''C:/Users/a b/repo''`.
   - Paths inside the wrapper use forward slashes (`C:/Users/...`).
   - `cd <worktree> && command timeout -k 10 900 ...` stays inside the one wrapped command, so the
     time limit and the `command` first word are bash's, exactly as verified.
   - One wrapped command per tool call, as today.
4. **Capture.** `jq` is run through the same wrapper. Reading a file with the agent's own file
   tool is also fine.
5. **Background launches** use whatever the agent's command tool offers; the time limit is inside
   the wrapped command either way.
6. **Where it is written.** `SKILL.md` "Shell first": three or four lines and a pointer.
   `references/agents.md` "Systems and shells": the wrapper rules above, each marked not tested
   until run.

## Verification

- **In CI (Windows job):** a PowerShell test in `scripts/tests/` that finds Git Bash as above and
  runs, through the wrapper, the time limit (124), a quoted path with a space, the fixed prompt
  reaching a stand-in program intact, and the four snapshot commands. The operator applies the
  workflow change, as before.
- **Live, on the Windows machine:** a new verification issue, same form as #51, for Agy and Codex
  from PowerShell: one Advise round with one member (`claude-haiku` on `claude-haiku-5-5`).
- **Guardrail:** how it judges a wrapped command is unknown. The live runs will show it. A denial
  is followed, reported in the run's comment, and filed on agent-guardrails; any fix is made in
  that repository, not worked around here.

## Left to the builder

Exact wording; the test's stand-in program; whether `agents.md` shows one worked example per
agent or one in total.

## Known risks

- Git Bash started with `-c` from PowerShell may not have the same `PATH` as an interactive Git
  Bash (`timeout`, `jq`, `claude`): not tested.
- Windows PowerShell 5.1 and PowerShell 7 may pass the string differently; the no-double-quote
  rule is meant to make that irrelevant: not tested.
- Codex may still be unable to coordinate after this, for the two reasons under Non-goals.
