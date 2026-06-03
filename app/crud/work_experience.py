from typing import Optional

from sqlalchemy.orm import Session

from app.models import WorkExperience
from app.schemas import DataSource, WorkExperienceCreate, WorkExperienceUpdate


def create(
    db: Session, *, candidate_id: int, data: WorkExperienceCreate
) -> WorkExperience:
    we = WorkExperience(
        candidate_id=candidate_id,
        company_name=data.company_name,
        job_title=data.job_title,
        start_date=data.start_date,
        end_date=data.end_date,
        description=data.description,
        resume_id=None,
        source=DataSource.manual,
    )
    db.add(we)
    db.commit()
    db.refresh(we)
    return we


def list_for_candidate(
    db: Session, candidate_id: int
) -> list[WorkExperience]:
    return (
        db.query(WorkExperience)
        .filter(WorkExperience.candidate_id == candidate_id)
        .order_by(
            WorkExperience.start_date.desc().nullslast(),
            WorkExperience.experience_id.desc(),
        )
        .all()
    )


def get(db: Session, experience_id: int) -> Optional[WorkExperience]:
    return db.get(WorkExperience, experience_id)


def update(
    db: Session, *, we: WorkExperience, data: WorkExperienceUpdate
) -> WorkExperience:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(we, key, value)
    db.commit()
    db.refresh(we)
    return we


def delete(db: Session, we: WorkExperience) -> None:
    db.delete(we)
    db.commit()
