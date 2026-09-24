# skills

Agent skills by CtrlCarlitos, installable with the [`skills`](https://skills.sh) CLI:

```sh
npx skills add CtrlCarlitos/skills -s code-search skill-creator -a claude-code opencode codex -g -y --copy
```

| Skill | What it does |
|---|---|
| [`code-search`](skills/code-search/SKILL.md) | Decide how to find code before grepping or opening a file: graft (repo graph) > serena (LSP) > rg > grep, gated on what is actually built and what file types are involved, with anti-loop rules. |

| [`skill-creator`](skills/skill-creator/SKILL.md) | Drop-in fork of Anthropic's skill-creator with Windows fixes (pipe reader, UTF-8 file I/O, `--project-root`, real-skill trigger detection). Pinned upstream commit and patch queue in `vendor/skill-creator/`; `scripts/sync-skill-creator.sh` rebuilds or checks it. Upstream issue anthropics/skills#1827; drop the fork once it lands. |

Each skill lives in `skills/<name>/SKILL.md`. Evals sit next to the skill in `evals/`.
