# AI-Assisted Coding Workflow (Codex Paradigm)

This repository now follows the workflow explained in Anindya Chakraborty’s essay, *AI Assisted Coding: Quicker Code Doesn’t Mean Higher Velocity* (Nov 9, 2025). The paper’s core claim is that AI agents shifted the bottleneck **from writing code** to **understanding, testing, and reviewing it**. To keep course materials and exercises honest we:

1. Plan each change in teacher-friendly, reviewable slices.
2. Generate code with assistants only inside those slices.
3. Split and annotate the output so humans can understand it quickly.
4. Run deterministic verification before asking for peer review.
5. Teach the above loop explicitly so students can reuse it outside the course.

This directory documents the paradigm Codex follows when touching this repo.

## Lifecycle Overview

| Loop | Human-owned questions | Assistant-owned tasks | Teaching hook |
| --- | --- | --- | --- |
| **Scope & Spec** | What problem are we solving? Where does it sit in the roadmap? | Draft initial outline/prompts once constraints are known. | Use Session 03 storyboard format; stress “one spec file per logical slice.” |
| **Prompt & Generate** | Define shape of the change (files, APIs, invariants). | Produce candidate code/tests/docs for the slice. | Model “drive, don’t delegate” pairing during live coding. |
| **Split & Annotate** | Group diffs into ≤150-line hunks, explain intent. | Suggest chunking + summary text. | Use the repo’s splitter/explainer workflow before PRs. |
| **Review & Transfer** | Validate maintainability, reject magic numbers, note risks. | Provide auto-generated review notes per hunk. | Run review checklist in Part C of labs. |
| **Verify & Publish** | Run pytest/ruff/mypy, re-read docs, ship. | Trigger local commands, highlight failures. | Every lab ends with the verification block already in the session doc. |

## Directory Structure

```
workflows/
└── ai-assisted/
    ├── README.md                   # Overview (this file)
    ├── teaching-guide.md           # How instructors narrate & grade the paradigm
    ├── repo-structure.md           # How this repo enforces the paradigm (spec folders, logs)
    ├── templates/
    │   └── feature-brief.md        # Template for “small, reviewable slice” briefs
    └── checklists/
        └── review.md               # Review + verification checklist tied to the PDF advice
```

## Using These Files

1. **Before prompting** – fill in `templates/feature-brief.md` so the scope stays under 150 LOC and the assistant knows the constraints.
2. **After generation** – run the splitter (or summarize manually) and attach annotations taught in `teaching-guide.md`.
3. **During review** – read `checklists/review.md` aloud with students; the PDF is explicit that reviewers must spend time understanding the change, so we make the questions concrete.
4. **During instruction planning** – `repo-structure.md` links each session doc to the workflow so the pedagogy stays consistent.

> **Reminder:** AI-written code is treated like external contributions. Assume nothing about correctness or maintainability until the checklists pass.
