# Council PowerShell Coordinator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A coordinator whose only command tool is PowerShell can run every council command by passing it, unchanged, to Git Bash.

**Architecture:** No new command set. The skill gains a wrapper rule (`& '<git-bash>' -c '<bash command>'`) and a quoting rule (single quotes only, doubled). A PowerShell test in `scripts/tests/` proves the wrapper carries the time limit, quoting, the fixed prompt and the snapshot commands.

**Tech Stack:** Markdown skill files, PowerShell 5.1 and 7, Git Bash, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-22-council-powershell-coordinator-design.md`

## Global Constraints

- No script or helper code in `skills/council/`.
- No bypass flag on any member; `command timeout -k 10 900` stays the start of every launch, inside the wrapper.
- Every new claim is marked `verified <date>`, `failed <date>` or `not tested`.
- `.github/workflows/ci.yml` is changed only by a patch the operator applies.
- A guardrail denial is followed and reported, never worked around.

## Review Focus

- A repository path containing a space: the wrapped command must still reach bash as one argument (tested in Task 1).
- A `$` or backtick inside the wrapped command: PowerShell must not expand it (tested in Task 1 with `$BASH_VERSION`).
- `C:\Windows\System32\bash.exe` (WSL) picked up in place of Git Bash: the skill text must rule it out (Task 2 wording; `uname -s` check in Task 1 on Windows).
- Windows PowerShell 5.1 against PowerShell 7: both run the test in CI (Task 1 patch).
- Git Bash started with `-c` lacking `timeout` on its path: the test's tool check fails loudly (Task 1).

---

### Task 1: PowerShell wrapper test

**Files:**
- Create: `scripts/tests/test_council_powershell.ps1`
- Patch for the operator: Windows job of `.github/workflows/ci.yml`, two steps after "council skill shell commands (Git Bash)": `shell: pwsh` and `shell: powershell`, each `run: ./scripts/tests/test_council_powershell.ps1`.

**Interfaces:**
- Produces: the wrapper form and bash-finding rule Task 2 documents.

- [ ] **Step 1:** Write the test. It finds bash (Windows: `bin\bash.exe` two levels up from `(Get-Command git).Source`; elsewhere: `bash` on `PATH`), prints PASS/FAIL per check like `test_council_commands.sh`, exits with the number of failures. Checks, each through `& $bash -c '<literal>'`:
  1. `echo $BASH_VERSION` prints a version (PowerShell expanded nothing).
  2. On Windows, `uname -s` starts with `MINGW` or `MSYS`.
  3. `command -v timeout`, `env`, `git`, `jq` each print a path.
  4. `command timeout -k 1 2 sleep 10` exits 124.
  5. `printf %s ''Read the brief at agent-to-agent/brief.md and follow it.''` prints exactly that sentence.
  6. In a temp repo whose path contains a space: `cd ''<path>'' && git rev-parse --show-toplevel` succeeds.
  7. The four snapshot commands, each as its own wrapped command with the quoted path, leave `git status --porcelain` unchanged and produce a commit containing an untracked file.
- [ ] **Step 2:** Run locally: `pwsh -NoProfile -File scripts/tests/test_council_powershell.ps1`. Expected: `0 check(s) failed`. To see a check fail first, run check 5 once with double quotes around the sentence removed and confirm FAIL, then restore.
- [ ] **Step 3:** Write the CI patch to the scratchpad and hand the operator the `! git apply` line.
- [ ] **Step 4:** Commit the test.

### Task 2: Skill text

**Files:**
- Modify: `skills/council/SKILL.md` ("Shell first" paragraph)
- Modify: `skills/council/references/agents.md` ("Systems and shells"; the two Windows coordinator lines)
- Modify: `skills/council/evals/evals.json` (one scenario, `documented-not-yet-run`)
- Modify: `README.md` (council row)

- [ ] **Step 1:** `SKILL.md`: the shell check has three outcomes: bash or zsh; PowerShell with Git Bash (run every command through the wrapper in `references/agents.md`); otherwise stop.
- [ ] **Step 2:** `agents.md`: a "From PowerShell" block with the finding rule, the wrapper, the quoting rule, one worked launch line, and a status on each line taken from Task 1's result (local PowerShell 7 on Linux only until CI runs).
- [ ] **Step 3:** One eval scenario: a PowerShell-only coordinator wraps the launch and uses no double quote.
- [ ] **Step 4:** Run `bash scripts/tests/test_council_commands.sh` and the PowerShell test; both `0 check(s) failed`. Commit.

### Task 3: Live verification request

- [ ] **Step 1:** Push the branch and open a PR.
- [ ] **Step 2:** File an issue in the form of #51 for Agy and Codex on Windows from PowerShell, with the wrapper and a line for any guardrail denial. Give the operator the prompt.
- [ ] **Step 3:** After the reports: update statuses; file any guardrail denial on agent-guardrails.
