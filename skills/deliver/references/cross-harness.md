# Cross-harness invocation and enforcement

Per the issue: separate procedural gates (what `deliver`'s prose says) from actual enforcement (what the harness blocks even if the prose were ignored). Claude Code's behavior below is confirmed live, from this very session. Antigravity, Codex, and OpenCode's are researched from each project's current documentation (checked 2026-10-18) but **not driven and confirmed live** -- real smoke tests on those three are deferred to #24, specifically so "documented" and "verified" stay distinct categories rather than quietly merging.

## Claude Code -- confirmed live

This session runs under an active guardrail plane the whole time: a `PreToolUse`-style hook layer that blocks destructive git commands, enforces worktree-isolation boundaries (a git command naming a path outside the current worktree is refused, not merely discouraged), and gates network egress to an allowlist requiring explicit operator approval per host. None of that is `deliver`'s own prose -- it's the host's enforcement, independent of whether `deliver` is installed or followed.

What this means for the three authorization states:

- **Discovery:** read-only tool calls (Read, Grep, git log/diff/show) are unrestricted; a write tool call (Edit, Write, a mutating Bash command) during discovery is a `deliver`-level discipline, not something Claude Code itself blocks by default -- the permission mode set for the session (not `deliver`) decides whether that write prompts, is auto-approved, or is denied. `deliver` does not claim Claude Code enforces its discovery boundary on its own; it relies on the session's configured permission mode plus the model actually following the skill's instructions.
- **Authorized implementation:** worktree isolation is enforced at the shell level by the guardrail hook, confirmed repeatedly this session (a command naming a path outside the active worktree is refused outright, requiring the command be split or re-targeted).

## OpenCode -- researched, not verified live

Has a genuine `permission` block (`opencode.json` or per-agent frontmatter) resolving each action to `allow`/`ask`/`deny`, matched by tool and, for `bash`, by command pattern (last-match-wins), with a documented example setting a review-style agent to deny edits and ask before bash. This is a real enforcement surface that *could* back `deliver`'s three states (e.g. deny edit/bash during discovery, allow during implementation) if a project's `opencode.json` is configured that way -- but `deliver` ships no such config and does not assume one exists; whether a given OpenCode installation actually enforces the boundary depends entirely on that installation's own permission config, which #24 should check for real rather than assume from the docs.

## Codex -- researched, not verified live

Has `sandbox_mode` (`read-only` / `workspace-write` / `danger-full-access`) and `approval_policy` as separate, real config keys in `config.toml`. `read-only` paired with `approval_policy = "never"` is documented as suited to exactly the kind of non-interactive, no-write discovery phase `deliver`'s Section 1 describes. `--dangerously-bypass-approvals-and-sandbox` exists and removes both; `deliver` must never instruct or imply that flag as part of any authorized state. As with OpenCode, actual enforcement depends on the installation's own `config.toml`, not on anything `deliver` ships -- #24 to confirm live.

## Antigravity -- researched, not verified live

Has permission presets (Default / Request Review / Turbo) plus layered allow/ask/deny rules (`read_file`/`write_file`/command patterns), with a documented precedence of Deny > Ask > Allow, and an important asymmetry: granting `write_file` on a path implicitly grants `read_file` there, and denying `read_file` on a path also blocks `write_file` there. "Request Review" is documented as the most restrictive preset (always asks for terminal commands, workspace-only file access) and is the closest existing match to `deliver`'s "discovery" state. Community reports describe UI/settings churn over time and at least one report of inconsistent enforcement -- another reason this needs a live check (#24), not an assumption from the docs alone.

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
