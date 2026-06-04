from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import job_posting as crud_job
from app.crud import search as crud_search
from app.database import get_db
from app.models import Employer
from app.schemas import (
    JobPostingCreate,
    JobPostingOut,
    JobPostingUpdate,
    JobStatus,
    WorkingMode,
)
from app.services.auth import get_current_employer
from app.utils.ownership import ensure_employer_owns_job
from app.utils.pagination import Page, PageParams

router = APIRouter(prefix="/job-postings", tags=["job-postings"])


@router.post(
    "",
    response_model=JobPostingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_job_posting(
    data: JobPostingCreate,
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> JobPostingOut:
    return crud_job.create(db, employer_id=employer.employer_id, data=data)


@router.get("", response_model=Page[JobPostingOut])
def list_job_postings(
    page: PageParams = Depends(),
    keyword: Optional[str] = Query(None, description="Keyword (FTS + synonyms)"),
    location: Optional[str] = Query(None),
    work_mode: Optional[WorkingMode] = Query(None),
    salary_range: Optional[str] = Query(None),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    fuzzy: bool = Query(False, description="Enable typo-tolerant matching (pg_trgm)"),
    db: Session = Depends(get_db),
) -> Page[JobPostingOut]:
    """Public job board. Supports all 4 modes: keyword, filter, keyword+filter,
    and fuzzy (typo-tolerant + synonym expansion via the synonyms service).

    Synonyms always apply when `keyword` is provided. `fuzzy=true` additionally
    enables pg_trgm similarity for typo tolerance (e.g. 'sofware enginer').
    """
    items, total = crud_search.search_jobs(
        db,
        keyword=keyword,
        location=location,
        work_mode=work_mode,
        salary_range=salary_range,
        status=status_filter,
        fuzzy=fuzzy,
        limit=page.limit,
        offset=page.offset,
    )
    return Page[JobPostingOut].build(
        [JobPostingOut.model_validate(j) for j in items], total, page
    )


@router.get("/{job_id}", response_model=JobPostingOut)
def get_job_posting(
    job_id: int, db: Session = Depends(get_db)
) -> JobPostingOut:
    job = crud_job.get(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job posting not found")
    return job


@router.patch("/{job_id}", response_model=JobPostingOut)
def update_job_posting(
    job_id: int,
    data: JobPostingUpdate,
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> JobPostingOut:
    job = crud_job.get(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job posting not found")
    ensure_employer_owns_job(job, employer)
    return crud_job.update(db, job=job, data=data)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_posting(
    job_id: int,
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> None:
    job = crud_job.get(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job posting not found")
    ensure_employer_owns_job(job, employer)
    crud_job.delete(db, job)
