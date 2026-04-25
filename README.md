# TaskAlloc API 🏗️
> Multi-role Employee & Task Allocation System — FastAPI + PostgreSQL + JWT

---

## Tech Stack

| Layer | Tool |
|---|---|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL (asyncpg driver) |
| Migrations | Alembic |
| Auth | JWT access + refresh tokens (python-jose + bcrypt) |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| Rate Limiting | slowapi |
| Testing | pytest + httpx (SQLite in-memory, no Postgres needed) |
| Containerisation | Docker + Docker Compose |

---

## Quick Start (Local — VS Code)

### 1. Clone & enter the project
```bash
cd taskalloc
```

### 2. Create & activate a virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
pip install aiosqlite          # only needed for running tests locally
```

### 4. Set up PostgreSQL
Create a database and user (or use Docker below):
```sql
CREATE USER taskalloc_user WITH PASSWORD 'taskalloc_pass';
CREATE DATABASE taskalloc_db OWNER taskalloc_user;
```

### 5. Configure environment
```bash
cp .env.example .env
# Edit .env if your DB credentials differ
```

### 6. Run migrations
```bash
alembic upgrade head
```

### 7. Seed sample data (first time only)
```bash
python seed.py
```
This creates:

| Role     | Email                  | Password       |
|----------|------------------------|----------------|
| ADMIN    | admin@taskalloc.com    | Admin@1234     |
| MANAGER  | manager@taskalloc.com  | Manager@1234   |
| EMPLOYEE | john@taskalloc.com     | Employee@1234  |

### 8. Start the server
```bash
uvicorn main:app --reload
```

Open Swagger UI → **http://localhost:8000/docs**

---

## Quick Start (Docker)

```bash
docker compose up --build
```
The API is available at **http://localhost:8000/docs**  
The database is at `localhost:5432`.

After containers start:
```bash
docker compose exec api python seed.py
```

---

## Running Tests

Tests use **SQLite in-memory** — no Postgres needed.

```bash
pytest                         # all 67 tests
pytest tests/test_auth.py -v   # one file
pytest -k "status"             # filter by name
pytest --tb=short              # compact output
```

---

## Project Structure

```
taskalloc/
├── app/
│   ├── core/
│   │   ├── config.py          # pydantic-settings env config
│   │   ├── database.py        # async SQLAlchemy engine + session
│   │   ├── dependencies.py    # get_current_user, require_role guards
│   │   ├── exceptions.py      # custom HTTP exception classes
│   │   ├── middleware.py      # AuditLog + RequestID middleware
│   │   ├── logging.py         # structured logger
│   │   └── security.py        # JWT, bcrypt, token hashing
│   │
│   ├── models/                # SQLAlchemy ORM models (UUIDs, soft delete)
│   │   ├── user.py            # User + Role enum
│   │   ├── department.py
│   │   ├── employee.py
│   │   ├── task.py            # Task + state machine + enums
│   │   ├── task_comment.py
│   │   ├── task_activity.py   # Auto-written activity log
│   │   ├── audit_log.py       # System-level request audit trail
│   │   └── refresh_token.py   # Hashed refresh tokens
│   │
│   ├── schemas/               # Pydantic v2 request/response models
│   ├── services/              # All business logic (no logic in routers)
│   └── routers/               # HTTP endpoints only — call services
│
├── migrations/                # Alembic async migrations
├── tests/                     # 67 pytest-asyncio tests (SQLite in-memory)
├── main.py                    # FastAPI app, middleware, router registration
├── seed.py                    # Bootstrap admin + sample data
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
└── .env.example
```

---

## API Overview

### Auth — `/auth`
| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Register new account |
| POST | /auth/login | Get access + refresh tokens |
| POST | /auth/refresh | Rotate access token |
| POST | /auth/logout | Revoke refresh token |
| GET | /auth/me | Current user profile |
| PATCH | /auth/me/password | Change own password |

### Tasks — `/tasks`
| Method | Path | Who |
|--------|------|-----|
| POST | /tasks | Admin / Manager |
| GET | /tasks | All (scoped by role) |
| GET | /tasks/{id} | All (scoped) |
| PATCH | /tasks/{id}/status | Role-gated state machine |
| PATCH | /tasks/{id}/assign | Admin / Manager |
| DELETE | /tasks/{id} | Admin (soft delete) |
| GET | /tasks/{id}/activity | All |

### Task Status State Machine
```
PENDING ──► IN_PROGRESS ──► UNDER_REVIEW ──► COMPLETED
   │              │                │
   └──────────────┴────────────────┴──► CANCELLED
```
- **Employee** can move: PENDING→IN_PROGRESS, IN_PROGRESS→UNDER_REVIEW
- **Admin/Manager** can move: UNDER_REVIEW→COMPLETED or →IN_PROGRESS, anything→CANCELLED

### Role Permissions
| Action | ADMIN | MANAGER | EMPLOYEE |
|--------|-------|---------|----------|
| Create employee | ✅ | ❌ | ❌ |
| Create department | ✅ | ❌ | ❌ |
| Create task | ✅ | ✅ (own dept) | ❌ |
| View all tasks | ✅ | ✅ (own dept) | ❌ |
| View own tasks | ✅ | ✅ | ✅ |
| Update task status | ✅ | ✅ | ✅ (own, limited) |
| Delete task (soft) | ✅ | ❌ | ❌ |
| View audit logs | ✅ | ❌ | ❌ |

---

## Design Decisions

- **UUIDs** instead of integer IDs (don't leak record counts)
- **Soft delete** on tasks and employees (`is_deleted`, `is_active` flags)
- **Refresh token rotation** — every refresh revokes the old token
- **Hashed refresh tokens** — raw token never stored in DB
- **Activity log** auto-written by service layer on every task mutation
- **Audit log** auto-written by middleware on every mutating HTTP request
- **State machine** enforced in service layer, not in DB or router
- **No business logic in routers** — routers call services, services touch DB

---

## Deployment (Render / Railway)

1. Push to GitHub
2. Create a new Web Service pointing at your repo
3. Set environment variables from `.env.example`
4. Set **Start Command**:
   ```
   alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Add a PostgreSQL database add-on and set `DATABASE_URL`

---

## Interview Talking Points

> "I built a multi-role task allocation backend with async FastAPI and PostgreSQL. The system implements a three-tier role model — admin, manager, employee — with JWT authentication using hashed access and refresh tokens. Tasks follow a defined state machine enforced at the service layer, with a full audit trail written automatically via middleware. The database uses UUIDs, soft deletes, and Alembic-managed async migrations. I wrote 67 tests against an in-memory SQLite database covering auth flows, RBAC rules, state machine transitions, filtering, and pagination. The system is containerised with Docker and ready to deploy on Render or Railway."
