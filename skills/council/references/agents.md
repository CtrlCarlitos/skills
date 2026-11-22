# Launching each agent as a council member

Every line below carries a status: `verified <date>` (it ran and did what the line says),
`failed <date>` (it ran and did not), or `not tested`. Treat anything that is not `verified` as
unknown. Unless a line says otherwise, the run behind it was made from a Claude Code 2.1.330
coordinator on Linux.

## Coordinators

Which agent can run this skill as coordinator. Apart from Claude Code, each line is one Advise
round with one member (`claude-haiku` on `claude-haiku-5-5`), reported in issue #51 of this
skill's repository; Review, Vote, a second round and more than one member: not tested there.

- **Claude Code 2.1.330, Linux, zsh:** every request in this file — verified 2026-11-21.
- **OpenCode v2.3.2, Linux, zsh:** the whole round and closing — verified 2026-11-21.
- **OpenCode v2.3.2, Windows, Git Bash:** the round, with a snapshot of uncommitted work and the
  Claude member's Start line — verified 2026-11-21. Closing — failed 2026-11-21: guardrail
  refused a command that chained the brief deletion with `rmdir`. The skill no longer runs
  `rmdir`; closing without it on Windows: not tested.
- **Agy 1.5.14, interactive, Linux, bash:** the whole round and closing — verified 2026-11-21.
  (Agy is unavailable as a member, below; as coordinator it is driven by the operator and works.)
- **Agy 1.5.11, Windows:** failed 2026-11-21. Its only command tool runs PowerShell, so it
  stopped at the shell check. That was before the "From PowerShell" wrapper below existed; Agy
  coordinating through the wrapper: not tested.
- **Codex 0.170.0, Linux, zsh:** failed 2026-11-21 at `git worktree add`: in the sandbox the
  session ran under, `.git` is read-only ("could not create leading directories of
  '.git/worktrees/...': Read-only file system"). A coordinator needs to write inside `.git`.
  Codex started in a mode that allows that: not tested.
- **Codex, Windows:** failed 2026-11-21. Its command tool runs PowerShell, and guardrail's hook
  refused every command before the shell check ("cannot prove the Windows command shell").
  Codex coordinating through the "From PowerShell" wrapper: not tested.

## Systems and shells

The commands are written for bash or zsh: `VAR=value command`, `< /dev/null`, the `command`
builtin, coreutils `timeout`, `env -u`, `jq`. PowerShell and `cmd` cannot run them as written. On
Windows the coordinator runs them in Git Bash: directly where its command tool is bash, through
the wrapper below where its command tool is PowerShell. `cmd` is not supported. WSL is Linux for
this purpose.

### From PowerShell

For a coordinator whose only command tool runs PowerShell. Every command in this skill stays as
written and is handed to Git Bash; nothing is translated.

- **Find Git Bash once.** `(Get-Command git).Source` prints where `git.exe` is, for example
  `C:\Program Files\Git\cmd\git.exe`. Git Bash is `bin\bash.exe` under that Git folder:
  `C:\Program Files\Git\bin\bash.exe`. Never `C:\Windows\System32\bash.exe`, which starts WSL.
  Confirm with `& 'C:\Program Files\Git\bin\bash.exe' -c 'echo $BASH_VERSION; uname -s'`: a
  version, then a name starting `MINGW` or `MSYS`. No Git Bash: stop and tell the operator.
- **The wrapper:** `& '<git-bash>' -c '<the bash command>'`, one wrapped command per call, with
  the literal path found above.
- **Quotes.** The bash command is one PowerShell single-quoted string, so PowerShell changes
  nothing in it. Inside it use single quotes only, each written twice (`''`), wherever this file
  or `SKILL.md` shows a quote of either kind. No double quote appears anywhere in the call.
- **Paths** inside the wrapper use forward slashes: `C:/Users/me/repo`.
- **`cd <worktree> && command timeout -k 10 900 ...` stays inside the one wrapped command**, so
  the time limit and the `command` first word are bash's.
- A Claude member's Start line, wrapped:

  ```
  & 'C:\Program Files\Git\bin\bash.exe' -c 'cd ''C:/Users/me/repo/.worktrees/council/<run>/claude-haiku'' && command timeout -k 10 900 env -u CLAUDECODE claude -p ''Read the brief at agent-to-agent/brief.md and follow it.'' --model claude-haiku-5-5 --permission-mode plan --permission-prompts none --output-format json < /dev/null > ''C:/Users/me/repo/agent-to-agent/<run>/raw/round-1/claude-haiku.json'''
  ```

Status. The wrapper and quoting rule are run by `scripts/tests/test_council_powershell.ps1` (the
time limit, `env -u`, the prompt arriving as one argument, a path with a space, the four snapshot
commands, a worktree, a stand-in launch line, closing), with no agent launched:

- Windows with Git Bash, on PowerShell 7.6 and on Windows PowerShell 5.1, in this repository's
  CI — verified 2026-11-22. Finding Git Bash from `git.exe` gave
  `C:\Program Files\Git\bin\bash.exe` there — verified 2026-11-22.
- PowerShell 7 with the bash of a Linux machine — verified 2026-11-22.
- An agent launched through the wrapper, and an agent coordinating from PowerShell: not tested.
- How guardrail judges a wrapped command: not tested.

"Shell commands" below means everything except launching an agent: the snapshot, the worktrees,
the brief copy, the time limit, closing. They are run in this skill's repository CI on all three
systems by `bash scripts/tests/test_council_commands.sh`, which prints PASS or FAIL for each.

- **Linux:** shell commands and every agent launch in this file — verified 2026-11-21.
- **Windows, Git Bash:** shell commands — verified 2026-11-21, including a native program being
  stopped at the time limit. Claude's Start line, from an OpenCode coordinator, answered on the
  requested model — verified 2026-11-21. Claude's Resume line, and every Codex and OpenCode
  member launch — not tested. `uuidgen` is missing there (failed 2026-11-21); nothing in this
  skill needs it.
- **macOS:** stock macOS has no `timeout` (failed 2026-11-21). With Homebrew `coreutils`
  installed, `timeout` is on `PATH` and every shell command passed, time limit included —
  verified 2026-11-21. Where `command -v timeout` prints nothing, tell the operator to install
  `coreutils`; writing its `gtimeout` name in place of `timeout`: not tested. A member is never
  launched without a time limit. Agent launches — not tested.
- **Long paths on Windows:** a member's worktree adds `.worktrees/council/<run>/<member>/` to
  every path; whether that trips the 260-character limit: not tested.

## Reading the command lines

- `<worktree>` is the member's own directory. `<prompt>` is always exactly
  `Read the brief at agent-to-agent/brief.md and follow it.` The coordinator copies the member's
  brief to that path inside `<worktree>` before launching.
- **`command` is the first word of every launch, and the agent's name is never the first word.**
  A shell alias is expanded only for the first word of a command. `timeout` and `env` start the
  binary found on `PATH` and never see aliases, so `command timeout -k 10 900 agy ...` runs the real
  `agy` even where `agy` is aliased to add a bypass flag (verified 2026-11-21: on a machine with
  that alias, every Agy launch in this form had its file tools auto-denied, which the bypass flag
  would have approved). A zsh global alias (`alias -g`) expands in any position and is not
  covered (not tested; none was defined). Writing `timeout -k 10 900 command agy ...`
  does not work: `command` is a shell builtin and `timeout` cannot run it (exit 127, failed
  2026-11-21).
- `900` is the 15 minute limit in seconds. Exit status `124` means the limit fired. `-k 10` kills
  a member that is still running 10 seconds after that (exit status `137`); a member that ignores
  the first signal: not tested.
- **Text that came from a member or a file never goes on a command line.** Inside double quotes
  the shell runs `$(...)` and backticks before the agent starts. `<prompt>` is always the fixed
  sentence above; on a Resume line it is `Read the new brief at agent-to-agent/brief.md and follow it.`, after the coordinator has replaced the copy (verified 2026-11-21 on Claude, Codex and OpenCode). The one value taken from output is a session id, and only
  when it has the form its **Session id** line gives (a uuid, or `ses_` plus letters and digits).
- `< /dev/null` keeps an agent from waiting on the coordinator's standard input. Every launch on
  2026-11-21 used it; launching without it: not tested.
- Run each launch from the member's directory: `cd <worktree> && command timeout -k 10 900 ...`.

## Claude

Status: available.

- **Start:** `command timeout -k 10 900 env -u CLAUDECODE claude -p "<prompt>" --model <model-id> --permission-mode plan --permission-prompts none --output-format json < /dev/null > <output-file>` — verified 2026-11-21.
- **Resume:** the Start line with `--resume <session-id>` added — verified 2026-11-21. Keep `--model <model-id>` on the resume line: with it the resumed turn answered on the member's model (verified 2026-11-21); without it, on the default model.
- **Answer:** the `result` field of the single JSON object in `<output-file>`, when `is_error` is `false`; `jq -r .result <output-file>` prints it — verified 2026-11-21.
- **Session id:** the `session_id` field of the output, a uuid Claude picks itself; unchanged by a resume — verified 2026-11-21. (`--session-id <uuid>` sets it up front and also works, verified 2026-11-21, but needs a uuid generator, which Git Bash on Windows lacks.)
- **Model:** `--model claude-haiku-5-5` (a full model id) answered on that model — verified 2026-11-21. `--model haiku` answered on `claude-sonnet-5-5` — failed 2026-11-21. The model that answered is the key under `modelUsage`; check it after every launch. An answer from another model is "no answer: wrong model".
- **Read-only:** `--permission-mode plan` with `--permission-prompts none` denied a file write; the denial is listed under `permission_denials` and no file appeared — verified 2026-11-21.
- **Brief access:** read `agent-to-agent/brief.md` inside its worktree — verified 2026-11-21. It can also read a brief outside its worktree (verified 2026-11-21), which the skill no longer relies on.
- **Version:** 2.1.330 (`command claude --version`) — verified 2026-11-21.

## Codex

Status: available.

- **Start:** `command timeout -k 10 900 codex exec --sandbox read-only -C <worktree> --json -o <reply-file> "<prompt>" < /dev/null > <events-file>` — verified 2026-11-21.
- **Resume:** `command timeout -k 10 900 codex exec resume <session-id> --json -o <reply-file> "<prompt>" < /dev/null > <events-file>`, run from `<worktree>` — verified 2026-11-21. The resume form lists neither `--sandbox` nor `-C` in its `--help` (verified 2026-11-21). Outside a git repository Codex is expected to need `--skip-git-repo-check`: not tested.
- **Answer:** the whole content of `<reply-file>` — verified 2026-11-21.
- **Session id:** `thread_id` on the first line of `<events-file>` (`"type":"thread.started"`); unchanged by a resume — verified 2026-11-21.
- **Model:** `-m <model>` — not tested. Without it Codex uses the operator's configured model, and the output does not name it; record the model as "configured default".
- **Read-only:** a write asked for on a resumed session was refused ("read-only filesystem access") and no file appeared — verified 2026-11-21.
- **Brief access:** read `agent-to-agent/brief.md` inside its worktree — verified 2026-11-21. It can also read a brief outside its worktree (verified 2026-11-21), which the skill no longer relies on.
- **Version:** codex-cli 0.170.0 (`command codex --version`) — verified 2026-11-21.

## OpenCode

Status: available; read-only by rule only.

- **Start:** `command timeout -k 10 900 opencode run --format json -m <provider/model> "<prompt>" < /dev/null > <events-file>` — verified 2026-11-21.
- **Resume:** the Start line with `--session <session-id>` added — verified 2026-11-21.
- **Answer:** the `part.text` value on the last line of `<events-file>` whose `type` is `text`; earlier `text` lines are progress notes, not the answer — verified 2026-11-21.
- **Session id:** `sessionID` on every line, of the form `ses_...`; unchanged by a resume — verified 2026-11-21.
- **Model:** `-m zai-coding-plan/glm-5.3` was accepted, but the output does not name the model that answered — not tested. `command opencode models` lists the ids.
- **Read-only:** by rule only: asked to create a file, it created it — verified 2026-11-21. Never add `--auto`.
- **Brief access:** read `agent-to-agent/brief.md` inside its worktree with its own read tool, nothing refused — verified 2026-11-21. Outside the worktree its read tool is refused ("external_directory ... auto-rejecting") and it falls back to a shell command (verified 2026-11-21); the skill no longer relies on that.
- **Version:** v2.3.2 (`command opencode --version`) — verified 2026-11-21.

## Agy

Status: unavailable as a member. Headless it cannot read any file, so it cannot read a brief, and
a brief's text may not be put on the command line. Record it as missing. The lines below are what
ran, kept for the day its file access changes.

- **Start:** `command timeout -k 10 900 agy --sandbox --output-format json --print="<prompt>" < /dev/null > <output-file>` — verified 2026-11-21 that it starts and answers a prompt that needs no file; it could not follow `<prompt>` because it could not read the brief.
- **Resume:** the Start line with `--conversation <session-id>` added before `--print=` — verified 2026-11-21.
- **Answer:** the `response` field of the single JSON object. An empty `response`, or a `denied_actions` field, means no answer, whatever `status` and the exit status say — verified 2026-11-21.
- **Session id:** `conversation_id`; unchanged by a resume — verified 2026-11-21.
- **Model:** `--model <id>` — not tested. `command agy models` lists the ids.
- **Read-only:** headless, a file write was denied (`denied_actions` named `write_file`) and no file appeared — verified 2026-11-21. Shell commands under `--sandbox` — not tested.
- **Brief access:** reading a file was denied (`denied_actions` named `read_file`), both outside its worktree and inside it, including `agent-to-agent/brief.md` — failed 2026-11-21. Adding `--mode plan`, or a `--settings` value with a `permissions.allow` rule for `read_file` (three spellings), did not change that — failed 2026-11-21. Agy's own error message names the bypass flag as the way round; that is never used, so: not tested.
- **Version:** 1.5.14 (`command agy --version`) — verified 2026-11-21.

## Hazards

- **OpenCode writes when asked; Agy cannot read.** OpenCode has no read-only switch, so its member
  is read-only by rule. The `git status --porcelain` check showed the file it wrote in its
  worktree (verified 2026-11-21); a write outside its worktree and the operator's checkout is
  not detected by anything in this skill. Agy headless denies every file tool, so it changes nothing but also sees
  nothing (verified 2026-11-21).
- **A hung member.** OpenCode has hung with no output on this machine before; it did not in
  five runs on 2026-11-21. With a 5 second limit every agent ended with exit status `124` and left
  no process behind (verified 2026-11-21). A turn that ends that way is "no answer".
- **Agy's exit status proves nothing.** It exited `0` with `"status":"SUCCESS"` and an empty
  `response` when a tool was denied (verified 2026-11-21). Read the result. A bare `--print`
  swallows the next flag; always write `--print=` (not tested here; carried from earlier findings).
- **A Claude member under a Claude coordinator** is launched with `env -u CLAUDECODE` (every
  Claude launch on 2026-11-21 used it; launching without it: not tested).
- **A member turn can outlast the coordinator's own command limit.** Launch members as background
  commands where the harness has them (not tested in the launch check).
- **Guardrail.** On a machine with guardrail, a launch, a worktree, or a write outside the
  session's repository may be denied or need the operator. On 2026-11-21 the launches were allowed;
  printing the environment and one long command chain were denied, and so was `rmdir` of an empty
  folder (from an OpenCode coordinator, on Linux and on Windows). Follow the answer, write one
  literal command per call, and never work around a denial.
- **Members leave tool litter.** A Claude or Codex member whose user configuration loads the
  Serena MCP server leaves an untracked `.serena/` directory in its worktree (verified
  2026-11-21). The `git status --porcelain` check will show it. Report it as tool litter, by name,
  and separately from a file the member itself wrote.
- **A member loads the operator's own configuration**, including plugins and hooks. A one-line
  Claude turn cost $0.18 on `claude-sonnet-5-5` and $0.009 on `claude-haiku-5-5` (verified
  2026-11-21). Say which model each member will use before launching.
