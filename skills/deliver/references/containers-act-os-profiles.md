# Containers, `act` rehearsal, and OS/desktop profiles: research summary

Per the issue's own framing (sections 7-8): these are "optional," "research, not a core dependency," and must "not delay the core skill." This v1 documents the decision criteria and defers the actual work to #23, rather than building provisioning code now.

## Containers / Docker / devcontainer-aware validation

Most work in this repository runs natively (plain `python3 -m unittest`, `bash scripts/sync-vendor.sh`) -- there is no existing Docker/Compose/devcontainer profile to integrate with yet. Building one speculatively, before any task in this repo actually needs it, would be exactly the "turn this into a container provisioning platform" the issue warns against.

**Decision for v1:** `deliver`'s local-validation contract (`scripts/validation_contract.py`) runs natively. If a future task genuinely needs a container-backed profile (reproducible image/tool versions, isolated test services), that's real, scoped work for #23 -- done against an actual need, with the image/architecture, task-source mounting strategy, and safe-permissions requirements the issue lists, not provisioned in the abstract here.

## `act` rehearsal

[`act`](https://nektosact.com/) runs GitHub Actions workflows locally via Docker. Worth noting now, evaluated later:

- Linux jobs commonly run in Docker under `act`, which is reasonable container-based rehearsal.
- **Windows/macOS jobs can also run on an already-available matching host** through `act`'s `-self-hosted` runner mapping -- this is not virtualization of Windows/macOS on a Linux machine, and it removes container isolation entirely when used. A green `act` run under `-self-hosted` proves less than it looks like it proves.
- `act` does not reproduce GitHub's actual runner images or GitHub-hosted service behavior exactly -- a green `act` rehearsal is not a substitute for the required GitHub check, only a cheaper early signal.

**Decision for v1:** not adopted. `deliver`'s local-validation contract already runs the exact commands CI runs, natively, which is a stronger and simpler signal than rehearsing the GitHub Actions YAML through a second tool. `act` becomes worth adopting if a task needs to rehearse something `validation_contract.py` can't reach (e.g. action-specific behavior, not just the `run:` steps) -- deferred to #23 for that case if it arises.

## OS/desktop profiles

This repository's own CI already runs on `ubuntu-latest`, `windows-latest`, and `macos-latest` (confirmed: `.github/workflows/ci.yml`) -- real coverage of all three OS families already exists at the hosted-CI level. What's genuinely missing, and genuinely optional per the issue, is desktop/GUI/interactive coverage beyond what a hosted CI runner provides (login sessions, reboot behavior, real desktop environments) -- not relevant to anything this repository's skills currently need, since none of them do GUI automation or OS-level installation testing the way dotfiles-style bootstrap work does.

**Decision for v1:** no provisioning, no provider selection. The leads the issue already gathered (Fly.io Sprites, AWS EC2 Windows/Mac, MacStadium Orka, existing GitHub-hosted OS jobs) are recorded in #23 for whoever picks that issue up, with the comparison criteria the issue specifies (OS/architecture, real desktop access, lifecycle, snapshots, privileges/reboot, startup time, billing, cleanup, secret isolation). No budget or lifecycle approval has been sought, matching the issue's own requirement that this not happen speculatively.

## Why defer rather than skip silently

All three of the above are filed as #23 specifically so this deferral is a recorded decision, not a thing someone has to rediscover was never done. None of them block `deliver`'s core acceptance criteria, which the issue itself separates out from "optional OS/desktop coverage... research, not a core dependency."
