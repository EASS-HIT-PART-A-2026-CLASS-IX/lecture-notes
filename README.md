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

## 🧠 Course Highlights

- Sessions 01–04: developer environment (Linux/WSL/macOS), HTTP/REST, FastAPI fundamentals, practical packaging with uv.
- Sessions 05–08: movie service persistence, Streamlit & Typer interfaces, testing/logging, and AI-assisted coding habits.
- Sessions 09–11: optional deep dives (async refreshers, Compose concepts, security vocabulary) for curious students—deliverables stay simple even if you browse these.
- Session 12: polish, demos, and tool-friendly API patterns.
- Exercises pace with the storyline:
  - **EX1** (due Tue 2 Dec 2025, 23:59 Israel time): ship a FastAPI + SQLModel CRUD API with a tiny SQLite database and tests.
  - **EX2** (due Tue 23 Dec 2025, 23:59 Israel time): deliver a Streamlit dashboard **or** Typer CLI that talks to the EX1 API.
  - **EX3** (assigned Mon 5 Jan 2026, final due Tue 10 Feb 2026, 23:59 Israel time): integrate the API and interface, add one thoughtful improvement, document the runbook. Everything runs locally; cloud, Docker, and security work are optional extras only.

## 🌱 Future-facing Engineering Archetypes
Modern software careers are coalescing around four builder profiles, and every lab in this repo intentionally hits each archetype so students can imagine their next role:

1. **Field / Business Engineer (the people person)** – Turns office-hour demos into “this solves your problem” stories and keeps customer value front and center.
2. **DevOps & Infrastructure Engineer (the reliability guru)** – Automates the boring parts: Docker Compose, repeatable env setup, health checks, and log-friendly services.
3. **Full-stack Product Engineer (the end-to-end builder)** – Ships UI, API, and persistence together; FastAPI + Streamlit reps are the backbone of the course.
4. **AI Full-stack Engineer (the intelligence layer)** – Wires agents, retrieval flows, and safe automation; Session 08 plus the optional MCP/DuckDB tracks pave that on-ramp.

**Course promise**: graduates leave day-one ready for archetypes 3–4, with enough automation muscle memory to be a smart bet for archetype 2 if a team mentors them. By constantly narrating stakeholder impact we keep archetype 1 in the conversation too, so students can explain their builds to humans, not just terminals.

## 🗂️ Legacy Materials

Historical slides and Natalie’s notes live under `lectures/`:

- `lectures/archive/` – previous slide decks and Makefile.
- `lectures/notes/` – Natalie’s comprehensive PDF reference.

These are preserved for reference but the new scripted sessions in `docs/` are the canonical teaching materials.

## 🤝 Contributing / Updating

1. Edit the relevant `docs/sessions/session-XX.md` file (each is standalone and self-contained).
2. Run through the verification commands provided in that session (most require `uv run pytest -q` or `curl` checks).
3. Commit changes and push to `main` (the repository is intentionally kept current for instructors).

If you spot an issue or want to suggest an improvement, open a GitHub issue or pull request with the session number in the title (e.g., `Session 05 – clarify rating fixture`).

Have a great semester!
