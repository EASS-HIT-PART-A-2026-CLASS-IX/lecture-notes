# Repo Structure Changes for the AI-Assisted Paradigm

The repo now encodes the workflow outlined in the “AI Assisted Coding: Quicker Code Doesn’t Mean Higher Velocity” PDF. This document points to the key spots.

## Reference Sources
- `docs/reference/ai-assisted-coding.txt` — text export of the PDF so every contributor can cite the primary source.
- `docs/workflows/ai-assisted/` — this folder with guides, templates, and checklists (see `README.md`).

## Mandatory Artifacts per Change
1. **Feature Brief** (stored anywhere under `docs/` or directly in the PR) using `templates/feature-brief.md` — proves the change was scoped before prompting.
2. **Split/Annotation Notes** — either produced via [armchr](https://github.com/armchr/armchr) or summarized manually, but always referenced in commits/PRs.
3. **Checklist Run** — reviewers confirm each item in `checklists/review.md` before merging.
4. **Verification Log** — reference the commands from the relevant session doc (usually `uv run pytest` + a curl/script). Add the output summary to the PR description.

## Directory Pointers
```
docs/
├── sessions/                    # canonical teaching scripts
├── reference/ai-assisted-*.txt  # verbatim article excerpt for quick quoting
├── workflows/
│   └── ai-assisted/
│       ├── README.md
│       ├── teaching-guide.md
│       ├── repo-structure.md
│       ├── templates/
│       │   └── feature-brief.md
│       └── checklists/
│           └── review.md
```

## Session Doc Hooks
- Every session that introduces non-trivial code now links to the workflow section in its “Before Class” or “Part B” steps. When updating a session file, add a line like:
  > “Scope this change using `workflows/ai-assisted/templates/feature-brief.md` before prompting your assistant.”
- Session 08’s AI lab should cross-link to this folder explicitly; see the TODO note inside that file.

## Git Hygiene Expectations
- Keep commits ≤150 LOC in touched files unless impossible (document why in the brief when that happens).
- Reference the brief ID in commit messages: `feat: repo-db brief-004 apply sqlite repository`.
- Attach the checklist results (`[x] Tests`, `[x] Review`, `[x] Split/Explain`) to PR templates.

## Tooling Integration
- Adopt `armchr` locally (documented in `docs/workflows/ai-assisted/README.md`) to split large diffs. Until an automated integration lands, copy the annotations into PR descriptions.
- Encourage `git worktree` usage for parallel AI sessions, mirroring the Reddit workflow quoted in `docs/reference/ai-assisted-coding.txt` comments.
