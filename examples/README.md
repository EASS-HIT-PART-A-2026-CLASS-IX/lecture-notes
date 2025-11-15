# Examples Policy

Core sessions intentionally build everything live directly from the scripts under `docs/sessions/`. To keep the maintenance surface tiny we no longer ship pre-solved FastAPI/Streamlit samples inside `examples/`.

- **Session 03** is the canonical FastAPI walkthrough—follow `docs/sessions/session-03.md` (copy/paste ready) to scaffold the movie service in class.
- Reuse the same pattern for later labs (Streamlit in Session 06, AI tooling in Session 08, etc.); those files are created during the session, not pre-committed here.
- Optional deep dives (for example the blockchain microservice demo described in `docs/optional/blockchain-microservices-demo.md`) will add their own subdirectories under `examples/` once the material is ready.

Want a quick smoke test without live coding? Hit the REST Client snippets in `examples.http`—they target the FastAPI project you build during Session 03.
