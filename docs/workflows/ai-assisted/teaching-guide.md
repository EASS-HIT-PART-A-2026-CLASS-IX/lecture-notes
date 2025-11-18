# Teaching Guide — AI-Assisted Workflow

This guide translates the PDF’s recommendations into classroom moves. Every time Codex (or an instructor) touches the repo, we model the same habits so students internalize them.

## Learning Goals
1. **Expose the new bottleneck** — students must see that code generation is cheap but understanding/testing is not.
2. **Practice working in reviewable slices** — no feature merges without a filled `feature-brief.md`.
3. **Normalize shared ownership** — both “author” and “reviewer” learn the code together, so we rely on annotations + checklist items to keep cognitive load manageable.
4. **Use AI as a pair, not an autopilot** — narrate the architecture first, then let the assistant fill in code under those constraints.

## 3-Block Lesson Structure
Each 45-minute block already has A/B/C structure. Layer the workflow like this:

| Session Block | What to model | Tools/Docs |
| --- | --- | --- |
| **Part A (theory)** | Draw the “old vs new bottleneck” chart from the PDF. Highlight why the repo has specs + checklists. | `workflows/ai-assisted/repo-structure.md` diagrams |
| **Part B (build)** | Live-fill `templates/feature-brief.md`, show the exact prompt you send to Codex/Claude, watch the diff, then split + annotate. | Template + `armchr` splitter (or manual grouping) |
| **Part C (deep dive)** | Run through `checklists/review.md` with students reviewing the Part B change. End with verification commands from the session doc. | Review checklist + existing lab verification |

## Session Mapping
- **Sessions 03–05:** Start using feature briefs when migrating FastAPI → SQLModel → Postgres. Emphasize “one slice per subsystem” (config, models, repo, tests).
- **Session 06:** Show how the same workflow applies to UI additions; spec the dashboard API surface first.
- **Session 07:** Tie the checklist to logging/tests so students see review + observability alignment.
- **Session 08:** Make this the capstone on AI pair programming—compare a “big prompt” vs “brief-driven slices” and measure review time.
- **Sessions 09–12:** Treat refactors/ops work the same way (brief + checklist + verification) so the habit persists.

## Classroom Prompts
1. **“Scope call”** — ask students to read the brief aloud before code generation. Partners must restate success criteria.
2. **“Split & tell”** — after the assistant produces code, students mark each logical chunk (≤150 LOC) and summarize what changed before anyone reviews.
3. **“Checklist stand-up”** — use the review checklist as a mini-retrospective; every student answers one bullet.
4. **“Ownership swap”** — have the reviewer explain the change back to the author; if they struggle, the annotations are insufficient.

## Teaching Tips
- Remind everyone that AI-written tests are not automatically trustworthy. Pair students so one writes/validates the tests while the other drives the implementation prompt.
- Celebrate when students delete or rewrite AI output. The PDF’s thesis is that understanding + maintainability trump raw LOC.
- Keep diffs small even in demos. If a live coding segment risks going beyond 150 LOC, pause and defer part of the change to the next block.
- Reference the article directly—drop the Medium link in session slides/notes so students can read the rationale outside class.
