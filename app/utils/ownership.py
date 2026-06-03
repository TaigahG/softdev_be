"""Ownership / authorization helpers.

These are plain functions (not FastAPI dependencies) because the caller has
already loaded the row — the helper just compares ownership and raises 403
on mismatch. Use them after a `db.get(...)` in route handlers.
"""
from fastapi import HTTPException, status

from app.models import Application, Candidate, Employer, JobPosting, WorkExperience


def _forbidden(detail: str = "forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def ensure_candidate_owns_work_experience(
    we: WorkExperience, candidate: Candidate
) -> None:
    if we.candidate_id != candidate.candidate_id:
        raise _forbidden("you do not own this work experience")


def ensure_employer_owns_job(job: JobPosting, employer: Employer) -> None:
    if job.employer_id != employer.employer_id:
        raise _forbidden("you do not own this job posting")


def ensure_employer_owns_application_job(
    application: Application, employer: Employer, db
) -> None:
    """Application is owned by the job's employer, not the candidate."""
    job = db.get(JobPosting, application.job_id)
    if job is None or job.employer_id != employer.employer_id:
        raise _forbidden("you do not own this application's job posting")
