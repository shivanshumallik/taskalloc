# TaskAlloc

A backend API for managing employees, departments and tasks — built with FastAPI and PostgreSQL.

I built this to get a proper understanding of how production backend systems are actually structured, not just "make it work" but make it the right way. Things like refresh token rotation, soft deletes, audit trails — stuff that gets skipped in tutorials but matters in real codebases.

---

## What it does

Three roles — Admin, Manager, Employee — each with different access levels. Admins manage the system, managers handle their department's tasks, employees work on what's assigned to them.

Tasks follow a defined workflow:

```
PENDING → IN_PROGRESS → UNDER_REVIEW → COMPLETED
                                ↓
                          IN_PROGRESS   (manager sends it back)

Any active task → CANCELLED  (admin only)
```

The state machine is enforced at the service layer — you can't skip steps or go backwards except where it's explicitly allowed. Every status change gets logged automatically with who did it and when.

---

## Stack

- **FastAPI** — async, fast, and the automatic Swagger docs are genuinely useful while building
- **PostgreSQL** with async SQLAlchemy 2.0
- **Alembic** for migrations
- **JWT** — short-lived access tokens (30 min) + hashed refresh tokens (7 days)
- **Pydantic v2** for request/response validation
- **slowapi** for rate limiting
- **pytest** + httpx for testing — runs against SQLite in-memory so no database needed to run the suite
- Docker + Docker Compose for local setup

---

## Project structure

```
app/
├── core/          # config, db session, JWT logic, middleware, custom exceptions
├── models/        # SQLAlchemy models (8 tables)
├── schemas/       # Pydantic request & response shapes
├── services/      # all business logic lives here, nothing else touches the DB
└── routers/       # HTTP endpoints only — each one calls a service and returns
```

The strict separation between routers and services was intentional. Routers don't make decisions — they just receive a request, call the right service function, and return the result. This made testing a lot cleaner and the codebase easier to reason about.

---

## A few design decisions worth mentioning

**UUIDs over integer IDs** — integer IDs leak information (a competitor can figure out how many users you have). UUIDs are opaque.

**Refresh tokens are hashed before storage** — the raw token goes to the client, only the SHA-256 hash is stored. If the database leaks, those tokens are useless.

**Soft delete everywhere** — tasks get `is_deleted = True`, employees get `is_active = False`. Nothing is ever actually removed. Real systems don't hard-delete because you always end up needing that data later.

**AuditLog has no foreign key to users** — intentional. If a user gets deleted, the audit history for what they did should still exist. Storing `user_id` as a plain string instead of a FK makes that possible.

**Activity log is written before the status update commits** — both happen in the same transaction, so they either both succeed or both fail. Writing it after would mean a failed commit loses the log entry.

---

## Running it locally

**Prerequisites:** Python 3.11+, PostgreSQL

```bash
# clone and enter
git clone https://github.com/yourusername/taskalloc.git
cd taskalloc

# virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# install
pip install -r requirements.txt
pip install aiosqlite          # only needed for tests
```

Set up the database:

```sql
CREATE USER taskalloc_user WITH PASSWORD 'taskalloc_pass';
CREATE DATABASE taskalloc_db OWNER taskalloc_user;
GRANT ALL PRIVILEGES ON DATABASE taskalloc_db TO taskalloc_user;
```

Copy `.env.example` to `.env` and update if your credentials differ. Then:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
python seed.py
uvicorn main:app --reload
```

API docs at `http://localhost:8000/docs`

Seed creates three accounts to test with:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@taskalloc.com | Admin@1234 |
| Manager | manager@taskalloc.com | Manager@1234 |
| Employee | john@taskalloc.com | Employee@1234 |

---

## Tests

```bash
pytest
```

67 tests covering auth flows, role-based access, state machine transitions (valid and invalid), soft deletes, filtering, pagination and activity logging. All run against SQLite in-memory — no Postgres connection needed.

```
tests/test_auth.py          — register, login, refresh, logout, password change
tests/test_tasks.py         — state machine, RBAC, filtering, pagination
tests/test_departments.py   — CRUD, soft delete, access control
tests/test_employees.py     — CRUD, scoped access, stats
tests/test_comments.py      — comment thread on tasks
tests/test_analytics.py     — overview stats, overdue tasks
tests/test_health.py        — health check endpoints
```

---

## API overview

Full docs available at `/docs` when the server is running. Quick summary:

| Group | Key endpoints |
|-------|--------------|
| Auth | register, login, refresh, logout, change password |
| Tasks | create, list (with filters), update, status transitions, assign, soft delete |
| Employees | create, list, stats per employee |
| Departments | CRUD, list employees in department |
| Analytics | task overview, per-employee stats, overdue list |
| Comments | add, edit, delete on any task |

GET /tasks supports filtering by status, priority, assignee, department, due date range, and free-text search across title and description, with sorting and pagination.

---

## Docker

```bash
docker compose up --build
docker compose exec api python seed.py
```

---

## What I'd add next

- Background task queue for email notifications when tasks are assigned or go overdue
- Structured JSON logging so it plays nicely with log aggregation tools
- GitHub Actions CI to run the test suite on every push
- The analytics queries currently pull everything into Python and aggregate there — at scale those should be SQL GROUP BY queries