# FolioHive — FastAPI + PostgreSQL backend

Minimal FastAPI backend with PostgreSQL, Alembic migrations, structured JSON logging, and Kubernetes deployment manifests (Minikube / CKAD lab).

## Project

- **Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL (psycopg binary), Alembic, Pydantic Settings
- **Entry point:** `src/app/app.py` → `app = FastAPI()` (module `app.app`, so uvicorn target is `app.app:app` — note: README/Dockerfile say `app.main:app`, this is a known discrepancy)
- **Working directory:** `src/` (requirements.txt, alembic.ini, .env all live here)

## Commands

Run all commands from `src/`:

| Action | Command |
|---|---|
| Create venv | `python3 -m venv venv && source venv/bin/activate` |
| Install deps | `pip install -r requirements.txt` |
| Dev server | `uvicorn app.app:app --host 127.0.0.1 --port 8000 --reload` |
| Health check | `curl http://127.0.0.1:8000/healthz` |
| Alembic migration | `alembic upgrade head` |
| Docker build | `docker build -t fastapi:local .` (run from `src/`) |
| Docker run | `docker run --name fastapi-local-test -p 8000:8000 fastapi:local` |

No test runner or linter is configured.

## Architecture

```
src/
├── app/
│   ├── __init__.py
│   ├── app.py           # FastAPI app instance, route handlers
│   ├── config.py        # Pydantic Settings (env → POSTGRES_*)
│   ├── db.py            # SQLAlchemy engine + session + Base
│   ├── models.py        # ORM models (User)
│   ├── schemas.py       # Pydantic request/response schemas
│   └── logging_config.py# JSON-structured logging via pythonjsonlogger
├── alembic/
│   ├── env.py           # Alembic env (reads settings from config.py)
│   └── versions/        # Migration scripts
├── alembic.ini
├── requirements.txt
├── .env                 # Local DB creds
└── Dockerfile
```

**Key modules (5 total):**

1. **`app/app.py`** — App lifecycle and 3 endpoints: `GET /healthz` (liveness), `GET /db-check` (readiness), `POST /user`, `GET /user`.
2. **`app/config.py`** — `Settings` Pydantic model loading from `.env`; builds `POSTGRES_DSN` at runtime from component env vars.
3. **`app/db.py`** — Single `engine` + `SessionLocal` factory. `Base` is the declarative base for all ORM models.
4. **`app/models.py` / `schemas.py`** — `User` ORM model (`id`, `email`); `UserCreate` / `UserOut` Pydantic models.
5. **`app/logging_config.py`** — Configures JSON-structured logging to stdout for all loggers (root, uvicorn).

**K8s:** Manifests in project root (`dapi.yaml` = backend Deployment/Service/HPA, `cdb.yaml` = PostgreSQL StatefulSet/PV/PVC, `bns.yaml` = Namespace, `secret/esecret.yaml` = Secret). Metrics-server manifest in `acomponents.yaml`. The backend deployment uses an init container to run `alembic upgrade head` before the main container starts.

## Conventions

- **Env-driven config:** All secrets and addresses come from environment variables (via Pydantic `BaseSettings`). Never hardcode DSNs.
- **Session-per-request:** Each handler creates its own `SessionLocal()` context manager. No dependency injection / `Depends()` for DB sessions (not yet migrated to that pattern).
- **JSON logging:** Always use `logging_config.configure_logging()` at startup (already called in `app.py`). Log to stdout, structured JSON.
- **Error handling:** DB errors in endpoints return HTTP 503 with the error detail. Startup table creation failures are silently caught (app still starts).
- **Alembic:** Migrations are the production path (`alembic upgrade head`). The `_startup` hook calls `Base.metadata.create_all()` as a fallback for demo/development — this is explicitly noted as not for production.
- **Naming:** Python snake_case. SQLAlchemy Mapped annotation style. Pydantic models use `from_attributes = True` for ORM integration.
- **No test suite** exists yet.

## Notes

(Add notes here as needed.)

