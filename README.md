# EASS – Engineering of Advanced Software Solutions (Course Materials)

This repository contains the fully scripted 12-session plan for the **EASS 8 – Engineering of Advanced Software Solutions** course. Each class blends 45 minutes of theory with two 45-minute hands-on blocks, and the entire arc follows a single project: building a movie catalogue with FastAPI, SQLModel, Typer, and Streamlit—no heavy infrastructure or security overhead required.

## 🚀 Quick Start for Instructors

```bash
git clone https://github.com/EASS-HIT-PART-A-2025-CLASS-VIII/lecture-notes.git
cd lecture-notes
```

Open the `docs/` folder (or load the repo in VS Code) to follow any session directly—no static site build is required.

Key documents:

- `docs/index.md` – entry point with links to every session and deadline summary.
- `docs/exercises.md` – specifications and rubrics for the three lightweight exercises.
- `docs/sessions/session-XX.md` – detailed talk tracks, copy/paste code, AI prompt kits, troubleshooting, and verification commands for each class.
- `docs/troubleshooting.md` – quick fixes for common environment issues (uv, imports, Redis, etc.).
- `examples.http` – ready-to-run VS Code REST Client requests for the movie API.
- `docs/workflows/ai-assisted/` – new Codex paradigm for working with AI assistants (briefs, checklists, teaching guide).

## 🧠 Course Highlights

- Sessions 01–04: developer environment (Linux/WSL/macOS), HTTP/REST, FastAPI fundamentals, and the first persistence swap (SQLite via SQLModel) with uv-powered packaging.
- Sessions 05–08: movie service persistence, Streamlit & Typer interfaces, testing/logging, and AI-assisted coding habits.
- Sessions 09–11: optional deep dives (async refreshers, Compose concepts, security vocabulary) for curious students—deliverables stay simple even if you browse these.
- Session 12: polish, demos, and tool-friendly API patterns.
- Exercises pace with the storyline:
  - **EX1** (due Tue 2 Dec 2025, 23:59 Israel time): ship the FastAPI CRUD service from Session 03 with tests/Docker; adopt Session 04’s SQLite upgrade as soon as you’re ready so persistence is solved before EX3.
  - **EX2** (due Tue 23 Dec 2025, 23:59 Israel time): deliver a Streamlit dashboard **or** Typer CLI that talks to the EX1 API.
  - **EX3** (assigned Mon 5 Jan 2026, final due Tue 10 Feb 2026, 23:59 Israel time): integrate the API, dedicated persistence layer, and interface into a local multi-service stack (3+ cooperating processes), add one thoughtful improvement, and document the runbook. Everything runs locally; cloud, Docker, and security work are optional extras only.
  - **Choose your own domain:** the live sessions use a movie catalogue as the teaching example, but students pick any narrow theme (recipes, books, robotics gear, etc.) and keep it for all three exercises.

## 🌱 Future-facing Engineering Archetypes
Modern software careers are coalescing around four builder profiles, and every lab in this repo intentionally hits each archetype so students can imagine their next role:

1. **Field / Business Engineer (the people person)** – Turns office-hour demos into “this solves your problem” stories and keeps customer value front and center.
2. **DevOps & Infrastructure Engineer (the reliability guru)** – Automates the boring parts: Docker Compose, repeatable env setup, health checks, and log-friendly services.
3. **Full-stack Product Engineer (the end-to-end builder)** – Ships UI, API, and persistence together; FastAPI + Streamlit reps are the backbone of the course.
4. **AI Full-stack Engineer (the intelligence layer)** – Wires agents, retrieval flows, and safe automation; Session 08 plus the optional MCP/DuckDB tracks pave that on-ramp.

**Course promise**: graduates leave day-one ready for archetypes 3–4, with enough automation muscle memory to be a smart bet for archetype 2 if a team mentors them. By constantly narrating stakeholder impact we keep archetype 1 in the conversation too, so students can explain their builds to humans, not just terminals.

## 🗂️ Legacy Materials

Historical slides and Natalie’s notes live under `old-lecture-notes/`:

- `old-lecture-notes/archive/` – previous slide decks and Makefile.
- `old-lecture-notes/notes/` – Natalie’s comprehensive PDF reference.

These are preserved for reference but the new scripted sessions in `docs/` are the canonical teaching materials.

## 🤝 Contributing / Updating

1. Edit the relevant `docs/sessions/session-XX.md` file (each is standalone and self-contained).
2. Run through the verification commands provided in that session (most require `uv run pytest -q` or `curl` checks).
3. Commit changes and push to `main` (the repository is intentionally kept current for instructors).

## 🧪 AI-Assisted Workflow (Codex Paradigm)

The repo is organized around the cycle described in Anindya Chakraborty’s *AI Assisted Coding: Quicker Code Doesn’t Mean Higher Velocity*. Before prompting an assistant, fill out `docs/workflows/ai-assisted/templates/feature-brief.md`, keep diffs under ~150 LOC chunks, and run the review checklist in `docs/workflows/ai-assisted/checklists/review.md`. The complete teaching plan for this workflow lives in `docs/workflows/ai-assisted/teaching-guide.md`; use it whenever you update a session or add new materials so students learn the same habits.

If you spot an issue or want to suggest an improvement, open a GitHub issue or pull request with the session number in the title (e.g., `Session 05 – clarify rating fixture`).

Have a great semester!
