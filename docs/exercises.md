# Exercises Overview

Every assignment is intentionally small, runs on a single laptop (Linux, WSL, macOS, or other Unix-like environments), and focuses on getting something working without detours into security hardening or cloud deployment. Students may explore the deeper labs in the session notes, but the required deliverables stay simple and local.

**AWS Educate prerequisite:** Complete a self-paced **AWS Educate** learning path at https://www.awseducate.com/ (free, no credit card required) covering **Compute, Storage, and Databases** fundamentals by **Sunday, 29/03/2026 at 23:59 (Israel time)**. Flag blockers early in `#helpdesk`.

**Deadline policy:** All graded submissions (EX1, EX2, EX3) are scheduled on weekdays and never on Shabbat.

```mermaid
gantt
    title Exercise Timeline 2026 (Semester B)
    dateFormat  DD/MM/YYYY
    axisFormat  %d/%m

    section Exercises
    EX1 – FastAPI Foundations (Backend)             :active, 16/03/2026, 30/03/2026
    EX2 – Friendly Interface (Frontend + Backend)   :27/04/2026, 18/05/2026
    EX3 – Full-Stack Microservices Build Window     :25/05/2026, 01/07/2026
    EX3 – Final Submission Window                   :29/06/2026, 01/07/2026
```

## Pick Your Domain Once, Reuse It Everywhere
- Choose a narrow real-world theme (movie catalogue, recipe box, book tracker, indie game backlog, etc.) on Day 1.
- Keep the same theme through EX1–EX3 so each exercise feels like an incremental release of one product.
- All instructions below reference "movies" as the live-coded classroom demo—replace it with your chosen theme while keeping the architectural scope identical.

## EX1 – FastAPI Foundations (Backend)
- **Assigned:** Monday, 16/03/2026
- **Due:** Monday, 30/03/2026 at 23:59 (Israel time)
- **Goal:** Ship the core backend microservice for your chosen domain using **FastAPI**, **Pydantic**, and pytest. This is the service you’ll reuse in every later exercise. Persistence starts in-memory and graduates to SQLite when you integrate Session 04’s guidance (mandatory before EX3, optional for the EX1 grading window).
- **Sessions to revisit:** [Session 02 – Introduction to HTTP and REST](sessions/session-02.md), [Session 03 – FastAPI Fundamentals](sessions/session-03.md), [Session 04 – Persisting the Movie Service](sessions/session-04.md).
- **Required Features:**
  - Endpoints: CRUD for your core resource (Session 03 shows `/movies`; tailor the nouns/fields to your theme). Optional extras belong in stretch goals, not the base grade.
  - Data layer may be in-memory (e.g., simple repository/dict) for the base grade. Plan to adopt Session 04’s SQLModel + SQLite implementation soon after—EX3 expects your backend to talk to a real persistence service with migrations/seeds instead of committing `.db` files.
  - Tests using `pytest` and FastAPI’s `TestClient` (cover happy-path listing and create/update/delete).
  - README explaining how to create the uv environment, run the API locally, and execute the tests.
> **Session guidance:** Session 03 is the canonical EX1 implementation (HTTP API, validators, pytest, Docker). Session 04 demonstrates how to layer SQLModel/SQLite under the same repository interface—treat it as a stretch for EX1 and required prep for EX3’s multi-service architecture.
- **Rubric (100 pts):** correctness 40, simplicity/readability 20, tests 20, documentation 20. Bonus (+5) for providing a tiny seed script or `.http` playground tailored to your domain.

## EX2 – Friendly Interface (Frontend connected to Backend)
- **Assigned:** Monday, 27/04/2026
- **Due:** Monday, 18/05/2026 at 23:59 (Israel time)
- **Heads-up:** This timeline is positioned after the April memorial/holiday cluster so teams can progress without collision with closures.
- **Goal:** Build a lightweight interface (Streamlit dashboard or Typer CLI) that talks to the EX1 backend for the same domain. Students should be able to exercise the core flows in under a minute from launch.
- **Sessions to revisit:** [Session 05 – PostgreSQL Foundations for the Movie Service](sessions/session-05.md), [Session 06 – Interface Options](sessions/session-06.md).
- **Required Features:**
  - Reuse the EX1 API as-is; do not add authentication or security prompts.
  - Allow users to list existing entries and add a new entry in under a minute from launch.
  - Provide one small extra (e.g., mark a favourite item, show a summary metric, or export to JSON/CSV).
  - Document how to run the API and the interface side-by-side on a local machine.
- **Rubric (100 pts):** working flows 40, user guidance (clear copy, prompts, or help text) 25, code clarity 20, documentation 15. Bonus (+5) if tests automate one interface workflow (e.g., calling the Typer command with `CliRunner` or snapshot testing a Streamlit script).

## EX3 – Full-Stack Microservices Final Project (KISS)
- **Assigned:** Monday, 25/05/2026
- **Final submission window opens:** Monday, 29/06/2026
- **Final due:** Wednesday, 01/07/2026 at 23:59 (Israel time)
- **Goal:** Finish a tidy local product by joining the EX1 backend, the dedicated persistence layer from Session 04, and the EX2 interface, then adding integrations with at least one additional microservice (LLM tool, reporting worker, notification service, etc.) plus documentation you wish every teammate handed you. Everything must run locally via `uv run`/`python -m` for scripts and `docker compose up` for the API + Redis + worker stack—no cloud hosting required, but Compose, telemetry, and security guardrails from Sessions 09–12 are now graded expectations.
- **Sessions to revisit:** [Session 07 – Testing and Diagnostics](sessions/session-07.md), [Session 08 – AI Pairing Tips](sessions/session-08.md), [Session 09 – Async Recommendation Refresh](sessions/session-09.md), [Session 10 – Docker Compose, Redis, and Service Contracts](sessions/session-10.md), [Session 11 – Security Foundations](sessions/session-11.md), [Session 12 – Tool-Friendly APIs and Final Prep](sessions/session-12.md). These later sessions deepen reliability, orchestration, security, and release polish—lean on the ones that strengthen your EX3 storyline.
- **Required Pieces:**
  - One Git repository containing at least three cooperating services: the FastAPI backend, a persistence layer (SQLite/SQLModel or equivalent), and a user-facing interface (Streamlit or Typer). Most strong submissions will add a fourth microservice (LLM tool via Pydantic AI, background worker, webhook listener, etc.). Document orchestration in `docs/EX3-notes.md`.
  - A `compose.yaml` plus `docs/runbooks/compose.md` instructions covering how to launch the API, Redis, and async worker, how to verify health/rate-limit headers, and how to run Schemathesis/pytest in CI.
  - Session 09’s async refresher deliverable: `scripts/refresh.py` with bounded concurrency, retries, and Redis-backed idempotency plus at least one `pytest.mark.anyio` test. Paste a Logfire or Redis trace excerpt into `docs/EX3-notes.md`.
  - Session 11’s security baseline: hashed credentials, at least one JWT-protected route with role checks, rotation steps captured in `docs/EX3-notes.md`, and tests that fail when a token is expired or missing scope.
  - One enhancement that makes the product nicer without increasing complexity—examples: searchable catalog filtering, weekly recommendation digest generated via a simple SQL query, a CSV import/export command, or a PDF/Markdown summary report.
  - Automated tests that cover the enhancement (unit tests, simple integration test, or Typer CLI exercise).
  - Local demo script: `uv run python -m app.demo` or `scripts/demo.sh` that walks graders through starting the API, launching the interface, and using the new feature.
- **Rubric (100 pts):** working integration 35, thoughtful enhancement 25, automation/tests 20, documentation/demo assets 20. Bonus (+5) for recording a ≤2 min screen capture showing the flow end-to-end (attach a local `.mp4` or shareable link).

> 🧭 **Scope guardrail:** If a feature smells like production security, massive data ingestion, or multi-service orchestration, it’s beyond scope. Keep it local, deterministic, and doable in a weekend.

## Submission Guidelines
1. Push code to the designated GitHub Classroom repository (single monorepo for EX1–EX3 is encouraged but not mandatory—clarify structure in your README).
2. Tag releases if requested (e.g., `ex1-final`). Use meaningful commit messages so instructors can review your progression.
3. Include an “AI Assistance” section in each README describing prompts/tools used and how outputs were verified locally.
4. Provide reproducible database setup via migrations or seed scripts; do not commit SQLite `.db` artifacts.
5. Late policy: 48-hour grace period with 10% deduction; communicate early if blockers appear.

## Support Channels
- Discord `#helpdesk` channel for quick questions (invite: https://discord.gg/EYjQrSmF7f).
- Weekly office hours (posted in class).
- Peer study sessions after select lectures (announced in Discord).
