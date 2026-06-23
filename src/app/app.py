import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .db import engine, SessionLocal
from .db import Base
from .models import User
from .schemas import UserCreate, UserOut

from app.logging_config import configure_logging
configure_logging()

logger = logging.getLogger(__name__)

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def _startup() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created / verified on startup")
    except SQLAlchemyError as e:
        logger.warning("Startup table creation failed (DB may be down)", extra={"error": str(e)})


# ── Probes ────────────────────────────────────────────────────────────

@app.get("/healthz")
def health_check():
    logger.info("Health check called")
    return {"status": "OK"}


@app.get("/db-check")
def db_check():
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            session.commit()
        logger.info("Database check succeeded")
        return {"status": "OK"}
    except SQLAlchemyError as e:
        logger.error("Database check failed", extra={"error": str(e)})
        return JSONResponse(status_code=503, content={"status": "ERROR", "error": str(e)})


# ── API endpoints ─────────────────────────────────────────────────────

@app.post("/user", response_model=UserOut)
def create_user(payload: UserCreate):
    logger.info("Creating user", extra={"email": payload.email})
    with SessionLocal() as session:
        user = User(email=payload.email)
        session.add(user)
        try:
            session.commit()
            logger.info("User committed to database", extra={"email": payload.email})
        except SQLAlchemyError as e:
            session.rollback()
            logger.error("Failed to create user", extra={"email": payload.email, "error": str(e)})
            raise HTTPException(status_code=503, detail=str(e))
        session.refresh(user)
        logger.info("User created successfully", extra={"user_id": user.id, "email": user.email})
        return user


@app.get("/user", response_model=list[UserOut])
def list_users():
    with SessionLocal() as session:
        try:
            users = session.query(User).order_by(User.id.asc()).all()
            logger.info("Fetched users from database", extra={"count": len(users)})
        except SQLAlchemyError as e:
            logger.error("Failed to list users", extra={"error": str(e)})
            raise e
    logger.info("Listed users", extra={"count": len(users)})
    return users


# ── Web UI ────────────────────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Foliohive — User Manager</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
        h1 { color: #1a1a2e; }
        form { display: flex; gap: 0.5rem; margin: 1rem 0; }
        input[type="email"] { flex: 1; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 0.5rem 1rem; background: #1a1a2e; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { opacity: 0.85; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #eee; }
        th { color: #666; font-weight: 600; }
        .error { color: #c0392b; margin: 0.5rem 0; }
        .empty { color: #999; font-style: italic; }
    </style>
</head>
<body>
    <h1>&#128100; Foliohive Users</h1>

    <form id="user-form">
        <input type="email" id="email-input" placeholder="user@example.com" required>
        <button type="submit">Add User</button>
    </form>
    <div id="error" class="error"></div>

    <table>
        <thead><tr><th>ID</th><th>Email</th></tr></thead>
        <tbody id="user-list"><tr><td colspan="2" class="empty">No users yet</td></tr></tbody>
    </table>

    <script>
        const form = document.getElementById('user-form');
        const emailInput = document.getElementById('email-input');
        const errorDiv = document.getElementById('error');
        const tbody = document.getElementById('user-list');

        async function loadUsers() {
            const res = await fetch('/user');
            const users = await res.json();
            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" class="empty">No users yet</td></tr>';
                return;
            }
            tbody.innerHTML = users.map(u =>
                `<tr><td>${u.id}</td><td>${u.email}</td></tr>`
            ).join('');
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            errorDiv.textContent = '';
            const email = emailInput.value.trim();
            const res = await fetch('/user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            if (!res.ok) {
                const body = await res.json();
                errorDiv.textContent = body.detail || 'Failed to create user';
                return;
            }
            emailInput.value = '';
            await loadUsers();
        });

        loadUsers();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root():
    logger.info("Serving web UI")
    return HTML_PAGE
