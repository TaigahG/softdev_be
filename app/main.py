import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  # register models on Base.metadata
from app.database import Base, engine, get_db
from app.routers import (
    applications,
    candidates,
    employers,
    job_postings,
    memberships,
    resumes,
    skills,
    work_experiences,
)

# Skip DDL when running tests (TESTING=1) — tests use dependency overrides
# and don't need a real DB. Production uvicorn boot runs create_all normally.
if not os.getenv("TESTING"):
    Base.metadata.create_all(
        bind=engine,
        tables=[t for t in Base.metadata.sorted_tables if t.schema != "auth"],
    )

app = FastAPI(title="Jobs Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router)
app.include_router(candidates.router)
app.include_router(work_experiences.router)
app.include_router(employers.router)
app.include_router(job_postings.router)
app.include_router(applications.router)
app.include_router(skills.router)
app.include_router(memberships.router)
app.include_router(memberships.webhook_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db unreachable: {e}")
    return {"status": "ok"}
