from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
    
from .db import engine, SessionLocal
from .db import Base
from .models import User
from .schemas import UserCreate, UserOut

from app.logging_config import configure_logging
configure_logging()

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
def _startup() -> None:
    # For demo: create tables automatically.
    # In production: prefer Alembic migrations.
    # If Postgres is down at startup, we don't want the whole API to fail.
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        # App can still start; /db-check and /user endpoints will surface DB errors.
        pass

# K8s liveness/readiness probe endpoint
@app.get("/healthz")
def health_check():
    return {"status": "OK"}

@app.get("/db-check")
def db_check():
    try:
        with SessionLocal() as session:
            # Lightweight check that connection works.
            session.execute(text("SELECT 1"))
            session.commit()
        return {"status": "OK"}
    except SQLAlchemyError as e:
        return JSONResponse(status_code=503, content={"status":"ERROR","error": str(e)})

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head>
            <title>Foliohive API</title>
        </head>
        <body>
            <h1>Welcome to the Foliohive API!</h1>
            <p>Use the /user endpoint to create and list users.</p>
        </body>
    </html>
    """

@app.post("/user", response_model=UserOut)
def create_user(payload: UserCreate):
    with SessionLocal() as session:
        user = User(email=payload.email)
        session.add(user)
        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise HTTPException(status_code=503, detail=str(e))
        session.refresh(user)
        return user


@app.get("/user", response_model=list[UserOut])
def list_users():
    with SessionLocal() as session:
        try:
            users = session.query(User).order_by(User.id.asc()).all()
        except SQLAlchemyError as e:
            raise e
        return users

