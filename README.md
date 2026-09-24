# skills

Agent skills by CtrlCarlitos, installable with the [`skills`](https://skills.sh) CLI:

```sh
npx skills add CtrlCarlitos/skills -s code-search -a claude-code opencode codex -g -y --copy
```

| Skill | What it does |
|---|---|
| [`code-search`](skills/code-search/SKILL.md) | Decide how to find code before grepping or opening a file: graft (repo graph) > serena (LSP) > rg > grep, gated on what is actually built and what file types are involved, with anti-loop rules. |

Each skill lives in `skills/<name>/SKILL.md`. Evals sit next to the skill in `evals/`.
