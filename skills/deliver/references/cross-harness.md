# Cross-harness invocation and enforcement

Per the issue: separate procedural gates (what `deliver`'s prose says) from actual enforcement (what the harness blocks even if the prose were ignored). All four harnesses below are now confirmed live (#24, 2026-10-18) via each harness's own non-interactive CLI (`codex exec`, `opencode run`, `agy --print`) against a real git fixture repo with deliver installed -- not inferred from documentation. Where a claim below is still documentation-only, it says so explicitly.

## Claude Code -- confirmed live

This session runs under an active guardrail plane the whole time: a `PreToolUse`-style hook layer that blocks destructive git commands, enforces worktree-isolation boundaries (a git command naming a path outside the current worktree is refused, not merely discouraged), and gates network egress to an allowlist requiring explicit operator approval per host. None of that is `deliver`'s own prose -- it's the host's enforcement, independent of whether `deliver` is installed or followed.

What this means for the three authorization states:

- **Discovery:** read-only tool calls (Read, Grep, git log/diff/show) are unrestricted; a write tool call (Edit, Write, a mutating Bash command) during discovery is a `deliver`-level discipline, not something Claude Code itself blocks by default -- the permission mode set for the session (not `deliver`) decides whether that write prompts, is auto-approved, or is denied. `deliver` does not claim Claude Code enforces its discovery boundary on its own; it relies on the session's configured permission mode plus the model actually following the skill's instructions.
- **Authorized implementation:** worktree isolation is enforced at the shell level by the guardrail hook, confirmed repeatedly this session (a command naming a path outside the active worktree is refused outright, requiring the command be split or re-targeted).

## Codex -- confirmed live: real, comprehensive, OS-level enforcement

`codex exec --sandbox read-only` genuinely blocks writes, regardless of mechanism. Confirmed three separate ways against a real fixture repo: a shell `echo > file` and `echo hello > file` both reported back as blocked ("read-only file system"), and -- the decisive check -- **no probe file was ever created on disk** across all three attempts. A `--sandbox workspace-write` control, run identically, both reported success and actually wrote the file, with a full `command_execution` item trail (`exit_code: 0`). `read-only` paired with `approval_policy = "never"` is exactly the non-interactive, no-write discovery phase `deliver`'s Section 1 describes, and it holds up: **CONFIRMED-WORKING**, if the installation sets it. `--dangerously-bypass-approvals-and-sandbox` exists and removes both; `deliver` must never instruct or imply that flag as part of any authorized state.

One real environment-specific wrinkle, worth recording so it isn't mistaken for a Codex behavior: on a machine with guardrail installed, guardrail wraps every Codex shell command with its own pre-check (visible directly in the raw `command_execution` item's `command` field -- a `zsh -lc` script literally containing a guardrail workdir-match guard ahead of the real command). That wrapper only verifies the working directory; it is not what produced the read-only denial above (guardrail's own audit trail, `guardrail explain`, shows no record for the write attempts at all) -- the denial is Codex's native sandbox, confirmed separately from guardrail's layer.

**Resume/finish**, tested live: given an existing `feature-resume-test` branch with one (empty) WIP commit and told to resume rather than start fresh, Codex correctly invoked the deliver skill, found the existing branch via real git inspection, correctly identified the commit as having no actual changes yet, and proposed reusing it -- no duplicate branch proposed. **CONFIRMED-WORKING.**

## OpenCode -- confirmed live: real config surface, but default is wide open

Has a genuine `permission` block (`opencode.json` or per-agent frontmatter) resolving each action to `allow`/`ask`/`deny`, matched by tool and, for `bash`, by command pattern (last-match-wins). This is a real enforcement surface that *could* back `deliver`'s three states if a project's `opencode.json` is configured that way. Confirmed live, though, that **the unconfigured default is allow-everything**: against a real fixture repo with no project-local permission config (and the global config's own `permission.bash` set to `"*": "allow"`, no `edit` key at all), an explicit shell write (`echo hello > file`) executed immediately with zero prompt, and the file was actually created. So `deliver`'s discovery boundary on OpenCode, absent an explicit deny-config, is **CONFIRMED-GAP by default** -- prose discipline only, exactly as this file used to assume, now confirmed rather than assumed.

The reverse case -- whether an explicit `permission.edit`/`permission.bash` deny rule, once configured, is actually honored -- is **UNTESTED here**, for a telling reason: on this machine, guardrail itself refuses to let an agent session write `opencode.json` at all ("this is Guardrail-protected machinery: never edit it from a session"), since that file can also disable guardrail's own OpenCode plugin. That refusal is itself a real, useful signal (an agent can't self-weaken or self-strengthen OpenCode's own permission surface from inside a session on a guardrail-protected machine), but it means this specific sub-question needs an operator-authored config file to verify, not something this session could complete unilaterally without working around a correct guardrail block.

**Resume/finish**, tested live: given the same `feature-resume-test` branch, OpenCode invoked the `deliver` skill, then explicitly chained into `using-git-worktrees` for its existing-isolation detection step ("I'll first apply its resume contract... I will not run setup, tests, or create a worktree/branch"), ran real `git status`/`branch --all`/`log --all`/`show`/`rev-list`/`merge-base` commands, and reached the same correct conclusion (branch exists, commit is empty, no remote, resume don't duplicate). **CONFIRMED-WORKING.**

## Antigravity -- confirmed live: two separate mechanisms, neither a comprehensive discovery boundary

Antigravity's headless CLI (`agy`) exposes two flags that sound like enforcement but turn out to cover different, narrower things than the documented GUI permission presets (Default / Request Review / Turbo with Deny > Ask > Allow precedence) describe -- this file previously treated those presets as the relevant mechanism; the CLI path `deliver` actually scripts against is different, and is what got tested:

- **`--mode plan` is prompt-level only, not a tool-level block.** Asked to write a probe file, Antigravity initially declined and explained, unprompted and correctly: `/plan` "injects a prompt-level instruction requiring me to create an implementation plan artifact and get your approval before modifying any workspace files... I have not called `write_to_file`... yet," and it offered to test whether the harness enforces a hard block. Told explicitly to override that and call `write_to_file` anyway, **it did, and the write succeeded** -- "the `write_to_file` call succeeded and was not blocked by the harness... `/plan` is implemented as a prompt-level `<ADDITIONAL_METADATA>` injection... rather than a hard tool-level permission block." **CONFIRMED-GAP:** a model that simply doesn't follow the injected instruction isn't stopped by anything else.
- **`--sandbox` is real OS-level enforcement, but only for the shell tool.** A shell write attempt (`run_command`) was genuinely blocked at the OS level -- the actual captured tool output is `bash: line 1: probe-agy-sandbox.txt: Read-only file system`, and no file was created. But the *same flag*, same session type, asked to write via the dedicated `write_to_file` tool instead of a shell command, **succeeded immediately** -- "Success: Created `probe-agy-sandbox-writetool.txt`... using `write_to_file`." **CONFIRMED-GAP (partial):** `--sandbox` restricts the terminal, not the file-edit tool, so it does not back a comprehensive discovery boundary either.

Net finding: as of 2026-10-18, there is no single `agy` CLI flag that gives `deliver`'s discovery state the same kind of comprehensive, model-can't-talk-its-way-out-of enforcement Codex's `--sandbox read-only` provides. `deliver` must not claim otherwise for Antigravity's headless CLI path. (The GUI's permission-preset system is a separate mechanism, still documentation-only -- not re-tested here since `deliver`'s scriptable invocation surface is the CLI.)

**Resume/finish**, tested live: given the same `feature-resume-test` branch, Antigravity (with `deliver` installed in its real global skills directory) `view_file`'d `SKILL.md`, ran real `git status -sb`/`branch -a`/`worktree list`/`log --all`/`show`/`ls-tree` commands across two rounds, and correctly reported the branch, the empty commit, the missing TDD evidence, and no remote -- staying read-only, no branch created. **CONFIRMED-WORKING.**

## Invocation surface (illustrative, not frozen)

A short explicit entry point plus an optional persistent-instruction snippet, per the issue -- the full procedure stays in `SKILL.md`, never duplicated into global/repository instructions:

```text
Deliver issue #123.
Deliver issue #123, but stop at the PR.
Deliver the current task from its existing branch/worktree.
```

The resume/finish form must detect and adopt existing work (an open branch, worktree, or PR for the task) rather than create duplicates -- same detection pattern `using-git-worktrees` Step 0 and `finishing-a-development-branch` Step 2 already use, which `deliver` reuses rather than reimplementing.

## Separating workflow selection from merge authority

Saying "deliver issue #123" selects the *workflow*. It is never, by itself, permission to push, merge, or delete anything -- Gate 2 explicitly asks "what endpoint is authorized" (implementation only / stop at PR / continue through merge and cleanup), and that answer is task-specific, not implied by the word "deliver." A repository's branch protection or a host's permission mode can independently block an action `deliver`'s own authorization would otherwise allow; `deliver` must never present that as a bug or try to work around it.
