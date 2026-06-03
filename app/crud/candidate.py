from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.crud.skill import get_or_create_skills
from app.models import Candidate, CandidateSkill, Resume
from app.schemas import CandidateUpdate, DataSource


def get_by_user_id(db: Session, user_id: UUID) -> Optional[Candidate]:
    return (
        db.query(Candidate)
        .options(
            joinedload(Candidate.skills),
            joinedload(Candidate.work_experiences),
        )
        .filter(Candidate.user_id == user_id)
        .first()
    )


def get_by_id(db: Session, candidate_id: int) -> Optional[Candidate]:
    return (
        db.query(Candidate)
        .options(
            joinedload(Candidate.skills),
            joinedload(Candidate.work_experiences),
        )
        .filter(Candidate.candidate_id == candidate_id)
        .first()
    )


def latest_resume_url(db: Session, candidate_id: int) -> Optional[str]:
    resume = (
        db.query(Resume)
        .filter(Resume.candidate_id == candidate_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    return resume.file_url if resume else None


def update(
    db: Session, *, candidate: Candidate, data: CandidateUpdate
) -> Candidate:
    """PATCH semantics: only fields explicitly set on `data` are applied.
    If `skills` is provided, ALL existing CandidateSkill rows for this
    candidate are dropped and replaced — parser entries are wiped (re-upload
    the resume to restore them).
    """
    fields = data.model_dump(exclude_unset=True)
    skills_list = fields.pop("skills", None)

    for key, value in fields.items():
        setattr(candidate, key, value)

    if skills_list is not None:
        db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id == candidate.candidate_id
        ).delete(synchronize_session=False)
        db.flush()
        skills = get_or_create_skills(db, skills_list)
        for skill in skills:
            db.add(
                CandidateSkill(
                    candidate_id=candidate.candidate_id,
                    skill_id=skill.skill_id,
                    source=DataSource.manual,
                    resume_id=None,
                )
            )

    db.commit()
    db.refresh(candidate)
    return candidate


def set_profile_picture(
    db: Session, *, candidate: Candidate, url: str
) -> Candidate:
    candidate.profile_picture = url
    db.commit()
    db.refresh(candidate)
    return candidate


def list_resumes(db: Session, candidate_id: int) -> list[Resume]:
    return (
        db.query(Resume)
        .filter(Resume.candidate_id == candidate_id)
        .order_by(Resume.uploaded_at.desc())
        .all()
    )
