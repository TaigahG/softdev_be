# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Early-stage FastAPI backend for a jobs platform. Wiring is in place but the domain layer is unimplemented:

- `app/schemas.py` — full Pydantic domain (entities, enums, `*Create`/`*Update`/`*Out` split). Treat as source of truth.
- `app/main.py` — FastAPI app titled `"Jobs Platform API"` with `/health` and `/health/db` (the latter runs `SELECT 1` via `get_db` and returns 503 on failure).
- `app/database.py` — SQLAlchemy `engine` / `SessionLocal` / `Base` / `get_db` dependency. Reads `DATABASE_URL` from `.env` via `python-dotenv` and raises at import time if missing. `pool_pre_ping=True` is on.
- `app/models.py` — still empty. SQLAlchemy models should inherit `Base` from `app.database` and mirror `schemas.py`.
- `app/crud/`, `app/routers/`, `app/services/` — empty directories. Intended layering: routers (HTTP) → services (business logic) → crud (DB access) → models (SQLAlchemy).

`requirements.txt` is committed: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `pydantic[email]`. Add new packages there rather than installing ad hoc. No `pyproject.toml`, README, migrations (Alembic), or test suite yet.

The target database is Supabase Postgres — see `.env.example` for connection-string guidance (session pooler `:5432` for long-running server, transaction pooler `:6543` for serverless).

## Domain model (from `app/schemas.py`)

The schema layer defines the full domain shape before any DB models exist, so treat `schemas.py` as the source of truth for entities, fields, and enums when implementing models / CRUD / routers.

Two user roles via `UserRole` enum drive the data model:

- **Candidate** side: `Candidate` has one-to-many `Resume`, `Education`, `WorkExperience`, and many-to-many `Skill` (through `CandidateSkill`). Resume-derived rows carry `source=parsed` and a `resume_id` back-reference; manually entered rows carry `source=manual` and null `resume_id`. `Resume.parse_status` tracks async parsing (`pending`/`success`/`failed`).
- **Employer** side: `Employer` posts `JobPosting`s with many-to-many `Skill` (through `JobSkill`). Postings have `status` draft/published.
- **Applications** link candidate → job with `status` pending/reviewed. `ApplicationOut` embeds either `candidate` or `job` depending on viewer perspective.
- **Membership** gates recommendation volume: `RecommendedJobsOut` / `RecommendedCandidatesOut` are unlimited for members, capped at 10 otherwise (`is_member` flag on the response).
- **Search** schemas (`JobSearchQuery`, `CandidateSearchQuery`) include a `fuzzy: bool` flag — the search/recommendation layer is expected to support both exact-filter and fuzzy matching modes.

When implementing models, mirror the `*Create` vs `*Out` split: `*Create` is the request shape (often includes parent FKs like `candidate_id`), `*Out` is the response shape (includes server-assigned IDs/timestamps and nested relations). `*Update` schemas use all-optional fields for PATCH semantics.
