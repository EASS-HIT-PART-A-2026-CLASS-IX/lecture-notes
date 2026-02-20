# EASS – Engineering of Advanced Software Solutions (12-Session Plan)

Welcome! This site hosts the 12-week plan for the EASS (Engineering of Advanced Software Solutions) course reboot. Everything is organized around short theory bursts followed by two hands-on blocks so undergrads can follow step by step.

- Classes meet on **Mondays** from **02/03/2026** through **01/06/2026** (Semester B 2026).
- Each meeting has **45 min theory** + **45 min hands-on build** + **45 min practice/extension**.
- Exercises are assigned in class with weekday deadlines that avoid Shabbat and official holiday closures.

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
- [Semester B 2026 calendar (Jewish calendar aligned)](#semester-b-2026-calendar-jewish-calendar-aligned)
- [Optional MCP Workshop](sessions/optional/mcp.md)
- [Optional DuckDB Mini-Lakehouse Lab](sessions/optional/DuckDBMiniLakehouse.md)
- [Storage engine cheat sheet](sessions/session-05.md#part-a-–-theory-highlights) (SQLite ↔ Postgres ↔ Redis ↔ DuckDB guidance)
- [Legacy slide archives](https://github.com/EASS-HIT-PART-A-2025-CLASS-VIII/lecture-notes/tree/main/old-lecture-notes/archive)
- [Troubleshooting tips](troubleshooting.md)
- [Team Topologies summary](sessions/optional/TeamTopologies.md)
- [DSPy + Pydantic AI agent lab](sessions/session-08.md#dspy-micro-lab)
- [Local llama.cpp fallback (Session 08)](sessions/session-08.md#local-llamacpp-fallback-gemma-3-270m)
- [Qdrant vector DB stretch (Session 08)](sessions/session-08.md#qdrant-vector-db-stretch-retrieval-ready-prompts)
- [AI-assisted workflow (Codex paradigm)](workflows/ai-assisted/README.md)

## Semester B 2026 Calendar (Jewish Calendar Aligned)
| Event | Date | Notes |
| --- | --- | --- |
| First day of Semester B (HIT) | 22/02/2026 | Institutional opening day |
| Semester B starts at Faculty of Design | 01/03/2026 | Faculty opening day |
| Purim happening (Student Union activity) | 01/03/2026 | Study break: 13:00-14:00 and 18:00-19:00 |
| Ta'anit Esther | 02/03/2026 | Study stops from 18:00 |
| Purim | 03/03/2026 | Holiday (no classes) |
| Last study day before Passover break | 31/03/2026 | Zoom learning day |
| Passover break | 01/04/2026-08/04/2026 | Holiday |
| First study day after Passover break | 09/04/2026 | Classes resume |
| Eve of Holocaust and Heroism Remembrance Day | 13/04/2026 | Classes end at 18:00 |
| Holocaust and Heroism Remembrance Day ceremony | 14/04/2026 | Study break: 10:00-11:00 |
| Memorial Day ceremony (fallen soldiers and victims of terror) | 20/04/2026 | Study break: 13:00-14:00 |
| Eve of Memorial Day | 20/04/2026 | Classes end at 18:00 |
| Memorial Day | 21/04/2026 | Holiday |
| Independence Day holiday | 22/04/2026 | Holiday |
| Shavuot holiday | 21/05/2026-22/05/2026 | Holiday |
| Last day of Semester B | 05/06/2026 | Unchanged by institute policy |
| Make-up days | 07/06/2026-08/06/2026 | Makeup for canceled holiday classes; English/general studies exams may occur |
| Semester B exams | 09/06/2026-03/07/2026 | Exam period |

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
    dateFormat  DD/MM/YYYY
    section Foundations
    Session\ 01 – Kickoff (Env, Git)         :milestone, 02/03/2026, 0d
    Session\ 02 – HTTP/REST Probing          :milestone, 09/03/2026, 0d
    Session\ 03 – FastAPI Fundamentals       :milestone, 16/03/2026, 0d
    Session\ 04 – SQLite Persistence         :milestone, 23/03/2026, 0d
    section Delivery
    Session\ 05 – PostgreSQL Foundations     :milestone, 30/03/2026, 0d
    Session\ 06 – Frontend Choices           :milestone, 13/04/2026, 0d
    Session\ 07 – Testing & Diagnostics      :milestone, 27/04/2026, 0d
    Session\ 08 – AI-Assisted Coaching       :milestone, 04/05/2026, 0d
    section Scale\ &\ Polish
    Session\ 09 – Async Recommendation Refresh   :milestone, 11/05/2026, 0d
    Session\ 10 – Docker Compose,\ Redis,\ and\ Service\ Contracts:milestone, 18/05/2026, 0d
    Session\ 11 – Security\ Foundations          :milestone, 25/05/2026, 0d
    Session\ 12 – Tool-Friendly APIs             :milestone, 01/06/2026, 0d
    section Assessments
    EX1\ Window                              :active, 16/03/2026, 30/03/2026
    EX2\ Window                              :active, 27/04/2026, 18/05/2026
    EX3\ Build\ Window                       :active, 25/05/2026, 01/07/2026
    EX3\ Final\ Submission\ Window           :active, 29/06/2026, 01/07/2026
```

## Course Schedule
1. [Session 01 – Kickoff and Environment Setup](sessions/session-01.md)
2. [Session 02 – Introduction to HTTP and REST](sessions/session-02.md)
3. [Session 03 – FastAPI Fundamentals](sessions/session-03.md)
4. [Session 04 – Persisting the Movie Service (SQLite + SQLModel)](sessions/session-04.md)
5. [Session 05 – PostgreSQL Foundations for the Movie Service](sessions/session-05.md)
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
- **EX1 – FastAPI Foundations (Backend)**: assigned **Monday, 16/03/2026** · due **Monday, 30/03/2026 at 23:59 (Israel time)**. Build the FastAPI CRUD API + tests from Session 03; add Session 04’s SQLite persistence as soon as you’re ready so the service is EX3-ready.
- **EX2 – Friendly Interface (Frontend connected to Backend)**: assigned **Monday, 27/04/2026** · due **Monday, 18/05/2026 at 23:59 (Israel time)**. Add a Streamlit dashboard or Typer CLI that calls the EX1 API.
- **EX3 – Full-Stack Microservices Final Project (KISS)**: assigned **Monday, 25/05/2026** · final submission window opens **Monday, 29/06/2026** · final due **Wednesday, 01/07/2026 at 23:59 (Israel time)**. Integrate the API, dedicated persistence layer, interface, and async/Redis worker into a multi-service stack, add one small improvement, and document the runbook + Compose workflow. Everything stays local—`uv run` + `docker compose up`, no cloud hosting required.
- **Choose your own theme:** the sessions demonstrate a movie service, but students pick any narrow domain on Day 1 and carry it through all three exercises.
- Sessions 9–12 continue the main storyline by hardening async flows, multi-service orchestration, security, and tool-friendly polish—each reinforces EX3 readiness while keeping the graded scope local and manageable.

## Teaching Philosophy
- Build every example live from the session scripts (no pre-solved `examples/` folders) so changes stay in sync and the cohort can follow the exact steps. Keep snippets tiny and copy/paste friendly when time is tight.
- Repeat concepts using the whiteboard sketches described in each session and the Natalie reference notes in `old-lecture-notes/notes/`.
- Keep optional extras (MCP workshop, DuckDB lab, blockchain demo) clearly labeled so students know the graded work stays lightweight and local.
- Encourage question “warm-ups”: students share what they tried before asking for help.

Happy teaching!
