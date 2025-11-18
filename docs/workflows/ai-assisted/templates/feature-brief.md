# Feature Brief Template

> Copy this into your PR or `docs/notes/` folder before prompting the assistant. Keep each brief scoped to a reviewable slice (≤150 LOC touched per file set).

- **Brief ID:** `brief-###`
- **Date / Session:** e.g., `2025-11-24 · Session 04`
- **Owner(s):** name(s) or pair
- **Intent (2 sentences max):** What outcome will this slice deliver?
- **Trigger:** link to exercise requirement, bug ticket, or session step.
- **Files/Areas allowed:** list concrete modules/files.
- **Non-goals:** what must *not* change in this slice?
- **Assistant prompt outline:** bullet list of instructions you will feed into Codex/Claude (order matters).
- **Verification commands:** enumerate the exact `uv run ...` steps and curl checks.
- **Review focus:** what should reviewers scrutinize? (edge cases, migrations, etc.)
- **Docs/Teaching update:** any session/README text that must be edited alongside the code.

When done, attach the completed brief to the PR and reference it in commit messages.
