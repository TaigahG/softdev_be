from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import work_experience as crud_we
from app.database import get_db
from app.models import Candidate
from app.schemas import (
    WorkExperienceCreate,
    WorkExperienceOut,
    WorkExperienceUpdate,
)
from app.services.auth import get_current_candidate
from app.utils.ownership import ensure_candidate_owns_work_experience

router = APIRouter(tags=["work-experiences"])


@router.get(
    "/candidates/me/work-experiences",
    response_model=list[WorkExperienceOut],
)
def list_my_work_experiences(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[WorkExperienceOut]:
    return crud_we.list_for_candidate(db, candidate.candidate_id)


@router.post(
    "/candidates/me/work-experiences",
    response_model=WorkExperienceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_my_work_experience(
    data: WorkExperienceCreate,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> WorkExperienceOut:
    return crud_we.create(db, candidate_id=candidate.candidate_id, data=data)


@router.patch(
    "/work-experiences/{experience_id}", response_model=WorkExperienceOut
)
def update_work_experience(
    experience_id: int,
    data: WorkExperienceUpdate,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> WorkExperienceOut:
    we = crud_we.get(db, experience_id)
    if we is None:
        raise HTTPException(status_code=404, detail="work experience not found")
    ensure_candidate_owns_work_experience(we, candidate)
    return crud_we.update(db, we=we, data=data)


@router.delete(
    "/work-experiences/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_work_experience(
    experience_id: int,
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> None:
    we = crud_we.get(db, experience_id)
    if we is None:
        raise HTTPException(status_code=404, detail="work experience not found")
    ensure_candidate_owns_work_experience(we, candidate)
    crud_we.delete(db, we)
