from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from typing import Optional

from fastapi import Query

from app.crud import candidate as crud_candidate
from app.crud import membership as crud_membership
from app.crud import recommendation as crud_recommendation
from app.crud import search as crud_search
from app.database import get_db
from app.models import Candidate, Employer
from app.schemas import (
    CandidateOut,
    CandidateUpdate,
    JobPostingOut,
    RecommendedJobsOut,
    ResumeOut,
    WorkingMode,
)
from app.services import storage
from app.services.auth import get_current_candidate, get_current_employer
from app.utils.pagination import Page, PageParams

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _to_out(db: Session, candidate: Candidate) -> CandidateOut:
    out = CandidateOut.model_validate(candidate)
    out.resume_url = crud_candidate.latest_resume_url(db, candidate.candidate_id)
    return out


@router.get("/me", response_model=CandidateOut)
def get_my_profile(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> CandidateOut:
    return _to_out(db, candidate)


@router.patch("/me", response_model=CandidateOut)
def update_my_profile(
    data: CandidateUpdate,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> CandidateOut:
    updated = crud_candidate.update(db, candidate=candidate, data=data)
    return _to_out(db, updated)


@router.get("/me/resumes", response_model=list[ResumeOut])
def list_my_resumes(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[ResumeOut]:
    return crud_candidate.list_resumes(db, candidate.candidate_id)


@router.get("/me/recommended-jobs", response_model=RecommendedJobsOut)
def get_my_recommended_jobs(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> RecommendedJobsOut:
    """Top-N published jobs ranked by fit. Non-members are capped at 10;
    active members get the full ranked list."""
    is_member = crud_membership.is_active_member(db, candidate.user_id)
    jobs = crud_recommendation.recommend_jobs_for_candidate(
        db, candidate=candidate, is_member=is_member
    )
    return RecommendedJobsOut(
        is_member=is_member,
        total=len(jobs),
        jobs=[JobPostingOut.model_validate(j) for j in jobs],
    )


@router.post("/me/profile-picture", status_code=status.HTTP_201_CREATED)
def upload_profile_picture(
    file: UploadFile = File(...),
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    url = storage.upload_image(storage.images_bucket(), file)
    crud_candidate.set_profile_picture(db, candidate=candidate, url=url)
    return {"url": url}


@router.get("/search", response_model=Page[CandidateOut])
def search_candidates(
    page: PageParams = Depends(),
    keyword: Optional[str] = Query(None, description="Keyword (FTS + synonyms)"),
    preferred_location: Optional[str] = Query(None),
    working_mode: Optional[WorkingMode] = Query(None),
    fuzzy: bool = Query(False, description="Enable typo-tolerant matching"),
    _employer: Employer = Depends(get_current_employer),   # employer-only
    db: Session = Depends(get_db),
) -> Page[CandidateOut]:
    """Employer-only candidate search. Same 4 modes as job search."""
    items, total = crud_search.search_candidates(
        db,
        keyword=keyword,
        preferred_location=preferred_location,
        working_mode=working_mode,
        fuzzy=fuzzy,
        limit=page.limit,
        offset=page.offset,
    )
    return Page[CandidateOut].build(
        [_to_out(db, c) for c in items], total, page
    )


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate_by_id(
    candidate_id: int,
    _employer: Employer = Depends(get_current_employer),   # employer-only view
    db: Session = Depends(get_db),
) -> CandidateOut:
    candidate = crud_candidate.get_by_id(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return _to_out(db, candidate)
