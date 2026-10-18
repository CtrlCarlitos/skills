# skills

Agent skills by CtrlCarlitos, installable with the [`skills`](https://skills.sh) CLI:

```sh
npx skills add CtrlCarlitos/skills -s code-search skill-creator show-me -a claude-code opencode codex antigravity -g -y --copy
```

| Skill | What it does |
|---|---|
| [`code-search`](skills/code-search/SKILL.md) | Decide how to find code before grepping or opening a file: graft (repo graph) > serena (LSP) > rg > grep, gated on what is actually built and what file types are involved, with anti-loop rules. |
| [`skill-creator`](skills/skill-creator/SKILL.md) | Drop-in fork of Anthropic's skill-creator with Windows fixes (pipe reader, UTF-8 file I/O, `--project-root`, real-skill trigger detection) and eval-validity fixes (contaminated results from an installed same-named skill, harness errors masked as a 0% score). Pinned upstream commit and patch queue in `vendor/skill-creator/` (disposition and audit findings in `DISPOSITION.md`); `scripts/sync-vendor.sh skill-creator` rebuilds or checks it. Upstream issue anthropics/skills#1827; drop the fork once it lands. |
| [`show-me`](skills/show-me/SKILL.md) | Drop-in fork of HumanLayer's show-me with a cross-platform artifact opener (native Windows, WSL, Linux, macOS, devcontainers) replacing the macOS-only `open` command. User-invoked only (`disable-model-invocation`) — not auto-triggered. That invocation-suppression isn't honored by OpenCode (confirmed upstream bug) and is unverified on Antigravity; see `vendor/show-me/DISPOSITION.md` and #12. Pinned upstream commit and patch queue in `vendor/show-me/`; `scripts/sync-vendor.sh show-me` rebuilds or checks it. |

Each skill lives in `skills/<name>/SKILL.md`. Evals sit next to the skill in `evals/`.
