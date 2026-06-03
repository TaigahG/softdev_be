from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.crud.skill import get_or_create_skills
from app.models import JobPosting, JobSkill
from app.schemas import (
    JobPostingCreate,
    JobPostingUpdate,
    JobStatus,
    WorkingMode,
)


def _sync_required_skills(
    db: Session, job_id: int, skill_names: list[str]
) -> None:
    """Replace ALL job_skills for this job with the given names."""
    db.query(JobSkill).filter(JobSkill.job_id == job_id).delete(
        synchronize_session=False
    )
    db.flush()
    skills = get_or_create_skills(db, skill_names)
    for skill in skills:
        db.add(JobSkill(job_id=job_id, skill_id=skill.skill_id))


def create(
    db: Session, *, employer_id: int, data: JobPostingCreate
) -> JobPosting:
    job = JobPosting(
        employer_id=employer_id,
        title=data.title,
        company_info=data.company_info,
        required_education=data.required_education,
        required_experience=data.required_experience,
        work_mode=data.work_mode,
        location=data.location,
        salary_range=data.salary_range,
        status=data.status,
    )
    db.add(job)
    db.flush()  # populate job.job_id

    if data.required_skills:
        _sync_required_skills(db, job.job_id, data.required_skills)

    db.commit()
    db.refresh(job)
    return job


def get(db: Session, job_id: int) -> Optional[JobPosting]:
    return (
        db.query(JobPosting)
        .options(joinedload(JobPosting.required_skills))
        .filter(JobPosting.job_id == job_id)
        .first()
    )


def list_with_filters(
    db: Session,
    *,
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    work_mode: Optional[WorkingMode] = None,
    status: Optional[JobStatus] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[JobPosting], int]:
    """Returns (items, total). Defaults to status=published — drafts are
    never returned by this list endpoint (employers see their own drafts
    via a separate path)."""
    query = db.query(JobPosting).options(
        joinedload(JobPosting.required_skills)
    )

    effective_status = status or JobStatus.published
    query = query.filter(JobPosting.status == effective_status)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                JobPosting.title.ilike(like),
                JobPosting.company_info.ilike(like),
            )
        )
    if location:
        query = query.filter(JobPosting.location.ilike(f"%{location}%"))
    if work_mode:
        query = query.filter(JobPosting.work_mode == work_mode)

    total = query.distinct(JobPosting.job_id).count()
    items = (
        query.order_by(JobPosting.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def update(
    db: Session, *, job: JobPosting, data: JobPostingUpdate
) -> JobPosting:
    fields = data.model_dump(exclude_unset=True)
    skills_list = fields.pop("required_skills", None)

    for key, value in fields.items():
        setattr(job, key, value)

    if skills_list is not None:
        _sync_required_skills(db, job.job_id, skills_list)

    db.commit()
    db.refresh(job)
    return job


def delete(db: Session, job: JobPosting) -> None:
    db.delete(job)
    db.commit()
