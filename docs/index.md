# EASS – Engineering of Advanced Software Solutions (12-Session Plan)

Welcome! This site hosts the 12-week plan for the EASS (Engineering of Advanced Software Solutions) course reboot. Everything is organized around short theory bursts followed by two hands-on blocks so undergrads can follow step by step.

- Classes meet on **Mondays** from Nov 3, 2025 through Jan 19, 2026.
- Each meeting has **45 min theory** + **45 min hands-on build** + **45 min practice/extension**.
- Exercises are assigned in class and always due on a **Tuesday** to give students time after the weekend.

> **Heads-up from Andrej Karpathy**  
> - Sleep beats all-nighters; aim for ~7½ hours before big work.  
> - Meet the material early and often—short sessions across days stick best.  
> - Try problems without notes so you know you can re-create the steps.  
> - Teach someone else what you learned; explaining makes it click.  
> - Visit office hours and sessions even if you only have small questions.  
> - Stop studying alone near the end—compare notes and fill gaps with peers.  
> - Never hand in early on tests; use every minute to check for silly misses.  
> - Grades matter, but real projects and references matter more—build things outside class.

## Quick Links
- [Course schedule by session](#course-schedule)
- [Exercise lineup and deadlines](exercises.md)
- [Optional MCP Workshop](sessions/optional/mcp.md)
- [Optional DuckDB Mini-Lakehouse Lab](sessions/optional/DuckDBMiniLakehouse.md)
- [Storage engine cheat sheet](sessions/session-05.md#part-a-–-theory-highlights) (SQLite ↔ Postgres ↔ Redis ↔ DuckDB guidance)
- [Legacy slide archives](https://github.com/EASS-HIT-PART-A-2025-CLASS-VIII/lecture-notes/tree/main/old-lecture-notes/archive)
- [Troubleshooting tips](troubleshooting.md)
- [Team Topologies summary](sessions/optional/TeamTopologies.md)
- [DSPy + Pydantic AI agent lab](sessions/session-08.md#dspy-micro-lab)
- [Local llama.cpp fallback (Session 08)](sessions/session-08.md#local-llamacpp-fallback-gemma-3-270m)
- [Qdrant vector DB stretch (Session 08)](sessions/session-08.md#qdrant-vector-db-stretch-retrieval-ready-prompts)

## Future-facing Engineering Archetypes
Modern software careers are coalescing around four complementary builder profiles, and EASS intentionally lets students rehearse each mindset while staying within an approachable scope.

1. **Field / Business Engineer (the people person)** – Owns discovery conversations, trims prototypes to the sharpest business value, and turns demos into “this solves your problem” stories.
2. **DevOps & Infrastructure Engineer (the reliability guru)** – Keeps systems observable and shippable; in this course that means Docker Compose fluency, health checks, and deterministic deploys for every lab.
3. **Full-stack Product Engineer (the end-to-end builder)** – Ships UI, API, and data layers together. FastAPI, Streamlit, and shared models appear across sessions so students get repeated reps on this archetype.
4. **AI Full-stack Engineer (the intelligence layer)** – Orchestrates services that learn and act safely. Session 08’s agent labs and the optional MCP/DuckDB tracks show how to wire data contracts for AI-heavy features.

**Course promise**: graduate students who are day-one ready for archetypes 3–4, while giving them enough automation/infra reps to be a smart bet for archetype 2 if a team decides to mentor them. We keep archetype 1 in view by narrating every build in stakeholder language, not just in console output.

## Visual Roadmap
```mermaid
gantt
    title EASS 12-Session Journey
    dateFormat  YYYY-MM-DD
    section Foundations
    Session\ 01 – Kickoff (Env, Git)         :milestone, 2025-11-03, 0d
    Session\ 02 – HTTP/REST Probing          :milestone, 2025-11-10, 0d
    Session\ 03 – FastAPI Fundamentals       :milestone, 2025-11-17, 0d
    Session\ 04 – Docker & Reverse Proxy     :milestone, 2025-11-24, 0d
    section Delivery
    Session\ 05 – Persistence                :milestone, 2025-12-01, 0d
    Session\ 06 – Frontend Choices           :milestone, 2025-12-08, 0d
    Session\ 07 – Testing & Diagnostics      :milestone, 2025-12-15, 0d
    Session\ 08 – AI-Assisted Coaching       :milestone, 2025-12-22, 0d
    section Scale\ &\ Polish
    Session\ 09 – Async Recommendation Refresh   :milestone, 2025-12-29, 0d
    Session\ 10 – Docker Compose,\ Redis,\ and\ Service\ Contracts:milestone, 2026-01-05, 0d
    Session\ 11 – Security\ Foundations          :milestone, 2026-01-12, 0d
    Session\ 12 – Tool-Friendly APIs             :milestone, 2026-01-19, 0d
    section Assessments
    EX1\ Window                              :active, 2025-11-10, 2025-12-02
    EX2\ Window                              :active, 2025-12-01, 2025-12-23
    EX3\ KISS\ Capstone                      :active, 2026-01-05, 2026-02-10
```

## Course Schedule
1. [Session 01 – Kickoff and Environment Setup](sessions/session-01.md)
2. [Session 02 – Introduction to HTTP and REST](sessions/session-02.md)
3. [Session 03 – FastAPI Fundamentals](sessions/session-03.md)
4. [Session 04 – Persisting the Movie Service (SQLite + SQLModel)](sessions/session-04.md)
5. [Session 05 – Movie Service Persistence with SQLite](sessions/session-05.md)
6. [Session 06 – Movie Dashboards with Streamlit & React](sessions/session-06.md)
7. [Session 07 – Testing, Logging, and Profiling Basics](sessions/session-07.md)
8. [Session 08 – Working with AI Coding Assistants (LM Studio, vLLM, or Google AI Studio)](sessions/session-08.md)
9. [Session 09 – Async Recommendation Refresh](sessions/session-09.md)
10. [Session 10 – Docker Compose, Redis, and Service Contracts](sessions/session-10.md)
11. [Session 11 – Security Foundations](sessions/session-11.md)
12. [Session 12 – Tool-Friendly APIs and Final Prep](sessions/session-12.md)

**Optional add-ons (extra labs beyond the 12-session arc):**  
- [MCP Workshop – Weather MCP Server](sessions/optional/mcp.md) for teams who want to ship MCP-compatible tools after Session 12.  
- [DuckDB Mini-Lakehouse Lab](sessions/optional/DuckDBMiniLakehouse.md) for students who want a local analytics sandbox that complements Session 05.

## Exercises at a Glance
- **EX1 – FastAPI Foundations**: assigned Mon Nov 10 · due Tue Dec 2, 2025. Build the FastAPI CRUD API + tests from Session 03; add Session 04’s SQLite persistence as soon as you’re ready so the service is EX3-ready.
- **EX2 – Friendly Interface**: assigned Mon Dec 1 · due Tue Dec 23, 2025. Add a Streamlit dashboard or Typer CLI that calls the EX1 API.
- **EX3 – Capstone Polish (KISS)**: assigned Mon Jan 5 · class check-in Tue Jan 20 · final Tue Feb 10, 2026. Integrate the API, dedicated persistence layer, interface, and async/Redis worker into a multi-service stack, add one small improvement, and document the runbook + Compose workflow. Everything stays local—`uv run` + `docker compose up`, no cloud hosting required.
- **Choose your own theme:** the sessions demonstrate a movie service, but students pick any narrow domain on Day 1 and carry it through all three exercises.
- Sessions 9–12 continue the main storyline by hardening async flows, multi-service orchestration, security, and tool-friendly polish—each reinforces EX3 readiness while keeping the graded scope local and manageable.

## Teaching Philosophy
- Build every example live from the session scripts (no pre-solved `examples/` folders) so changes stay in sync and the cohort can follow the exact steps. Keep snippets tiny and copy/paste friendly when time is tight.
- Repeat concepts using the whiteboard sketches described in each session and the Natalie reference notes in `old-lecture-notes/notes/`.
- Keep optional extras (MCP workshop, DuckDB lab, blockchain demo) clearly labeled so students know the graded work stays lightweight and local.
- Encourage question “warm-ups”: students share what they tried before asking for help.

Happy teaching!
