from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Employer
from app.schemas import EmployerUpdate


def get_by_user_id(db: Session, user_id: UUID) -> Optional[Employer]:
    return (
        db.query(Employer).filter(Employer.user_id == user_id).first()
    )


def get_by_id(db: Session, employer_id: int) -> Optional[Employer]:
    return db.get(Employer, employer_id)


def update(
    db: Session, *, employer: Employer, data: EmployerUpdate
) -> Employer:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(employer, key, value)
    db.commit()
    db.refresh(employer)
    return employer


def set_profile_picture(
    db: Session, *, employer: Employer, url: str
) -> Employer:
    employer.profile_picture = url
    db.commit()
    db.refresh(employer)
    return employer


def set_company_picture(
    db: Session, *, employer: Employer, url: str
) -> Employer:
    employer.company_picture = url
    db.commit()
    db.refresh(employer)
    return employer
