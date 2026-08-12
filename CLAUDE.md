# Claude Code project instructions

@AGENTS.md

`AGENTS.md` is the single source of truth for shared project rules. This file
only provides Claude Code's native import and skill wayfinding; do not copy
shared architecture, safety, verification, or Git rules back into this file.

## Engineering skill wayfinding

- GitHub Issues are the issue and PRD tracker for `langhuanaibu/my-blog`.
  Use `gh` according to `docs/agents/issue-tracker.md`.
- Triage uses `needs-triage`, `needs-info`, `ready-for-agent`,
  `ready-for-human`, and `wontfix`; see `docs/agents/triage-labels.md`.
- Before daily-news domain work, read `CONTEXT.md` and the relevant ADRs as
  described in `docs/agents/domain.md`.
