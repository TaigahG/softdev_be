from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import application as crud_application
from app.crud import job_posting as crud_job
from app.database import get_db
from app.models import Candidate, Employer
from app.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.services.auth import get_current_candidate, get_current_employer
from app.utils.ownership import (
    ensure_employer_owns_application_job,
    ensure_employer_owns_job,
)

# Single router so wiring stays simple. Routes use full paths because they
# straddle two prefixes (/applications and /job-postings/.../applications).
router = APIRouter(tags=["applications"])


@router.post(
    "/applications",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def apply(
    data: ApplicationCreate,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    # The body carries candidate_id for schema compatibility but it's ignored —
    # we always trust the JWT.
    try:
        return crud_application.create(
            db, candidate_id=candidate.candidate_id, data=data
        )
    except crud_application.DuplicateApplicationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you have already applied to this job",
        )


@router.get("/applications/me", response_model=list[ApplicationOut])
def list_my_applications(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[ApplicationOut]:
    return crud_application.list_for_candidate(db, candidate.candidate_id)


@router.get(
    "/job-postings/{job_id}/applications",
    response_model=list[ApplicationOut],
)
def list_job_applications(
    job_id: int,
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> list[ApplicationOut]:
    job = crud_job.get(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job posting not found")
    ensure_employer_owns_job(job, employer)
    return crud_application.list_for_job(db, job_id)


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application_status(
    application_id: int,
    data: ApplicationUpdate,
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    application = crud_application.get(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="application not found")
    ensure_employer_owns_application_job(application, employer, db)
    return crud_application.mark_status(
        db, application=application, status=data.status
    )
