from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Application
from app.schemas import ApplicationCreate, ApplicationStatus


class DuplicateApplicationError(Exception):
    """Raised when (candidate_id, job_id) already exists."""


def create(
    db: Session, *, candidate_id: int, data: ApplicationCreate
) -> Application:
    application = Application(
        candidate_id=candidate_id,
        job_id=data.job_id,
        cover_letter=data.cover_letter,
        status=ApplicationStatus.pending,
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateApplicationError()
    db.refresh(application)
    return application


def get(db: Session, application_id: int) -> Optional[Application]:
    return db.get(Application, application_id)


def list_for_candidate(
    db: Session, candidate_id: int
) -> list[Application]:
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.candidate_id == candidate_id)
        .order_by(Application.applied_at.desc())
        .all()
    )


def list_for_job(db: Session, job_id: int) -> list[Application]:
    return (
        db.query(Application)
        .options(joinedload(Application.candidate))
        .filter(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
        .all()
    )


def mark_status(
    db: Session, *, application: Application, status: ApplicationStatus
) -> Application:
    application.status = status
    db.commit()
    db.refresh(application)
    return application
