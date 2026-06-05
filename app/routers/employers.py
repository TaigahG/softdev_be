from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.crud import employer as crud_employer
from app.crud import job_posting as crud_job
from app.database import get_db
from app.models import Employer
from app.schemas import EmployerOut, EmployerUpdate, JobPostingOut
from app.services import storage
from app.services.auth import AuthUser, get_current_employer, get_current_user
from app.utils.pagination import Page, PageParams

router = APIRouter(prefix="/employers", tags=["employers"])


@router.get("/me", response_model=EmployerOut)
def get_my_profile(
    employer: Employer = Depends(get_current_employer),
) -> EmployerOut:
    return employer


@router.patch("/me", response_model=EmployerOut)
def update_my_profile(
    data: EmployerUpdate,
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> EmployerOut:
    return crud_employer.update(db, employer=employer, data=data)


@router.post("/me/profile-picture", status_code=status.HTTP_201_CREATED)
def upload_profile_picture(
    file: UploadFile = File(...),
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    url = storage.upload_image(storage.images_bucket(), file)
    crud_employer.set_profile_picture(db, employer=employer, url=url)
    return {"url": url}


@router.post("/me/company-picture", status_code=status.HTTP_201_CREATED)
def upload_company_picture(
    file: UploadFile = File(...),
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    url = storage.upload_image(storage.images_bucket(), file)
    crud_employer.set_company_picture(db, employer=employer, url=url)
    return {"url": url}


@router.get("/me/job-postings", response_model=Page[JobPostingOut])
def list_my_job_postings(
    page: PageParams = Depends(),
    keyword: Optional[str] = Query(None),
    employer: Employer = Depends(get_current_employer),
    db: Session = Depends(get_db),
) -> Page[JobPostingOut]:
    items, total = crud_job.list_by_employer(
        db,
        employer_id=employer.employer_id,
        keyword=keyword,
        limit=page.limit,
        offset=page.offset,
    )
    return Page[JobPostingOut].build(
        [JobPostingOut.model_validate(j) for j in items], total, page
    )


@router.get("/{employer_id}", response_model=EmployerOut)
def get_employer_by_id(
    employer_id: int,
    _user: AuthUser = Depends(get_current_user),   # any authenticated user
    db: Session = Depends(get_db),
) -> EmployerOut:
    employer = crud_employer.get_by_id(db, employer_id)
    if employer is None:
        raise HTTPException(status_code=404, detail="employer not found")
    return employer
