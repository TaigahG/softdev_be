from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.crud.skill import get_or_create_skills
from app.models import (
    Candidate,
    CandidateSkill,
    Resume,
    WorkExperience,
)
from app.schemas import DataSource, ParseStatus
from app.services.parsed_resume import ParsedWorkExperience


def create(
    db: Session,
    *,
    candidate_id: int,
    file_name: str,
    file_type: str,
    file_url: str,
) -> Resume:
    resume = Resume(
        candidate_id=candidate_id,
        file_name=file_name,
        file_type=file_type,
        file_url=file_url,
        parse_status=ParseStatus.pending,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def get(db: Session, resume_id: int) -> Resume | None:
    return db.get(Resume, resume_id)


def mark_status(db: Session, resume_id: int, status: ParseStatus) -> None:
    resume = db.get(Resume, resume_id)
    if resume is None:
        return
    resume.parse_status = status
    db.commit()


def insert_parsed_children(
    db: Session,
    *,
    resume_id: int,
    candidate_id: int,
    education_level: Optional[str],
    field_of_study: Optional[str],
    work_experiences: Sequence[ParsedWorkExperience],
    skill_names: Sequence[str],
) -> None:
    """Atomically write parsed work experience + skills, and fill in education
    fields on the candidate row when they're still empty.

    WorkExperience and CandidateSkill carry resume_id + source='parsed' so
    deleting the resume nulls them (not deletes them) and user edits survive.
    Education is flat on the candidate now (single entry); the parser only
    fills it when the user hasn't entered it themselves.
    """
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise ValueError(f"candidate {candidate_id} not found")

    # Only fill candidate education if currently empty — don't clobber user input.
    if education_level and not candidate.education_level:
        candidate.education_level = education_level
    if field_of_study and not candidate.field_of_study:
        candidate.field_of_study = field_of_study

    for exp in work_experiences:
        db.add(
            WorkExperience(
                candidate_id=candidate_id,
                resume_id=resume_id,
                company_name=exp.company_name,
                job_title=exp.job_title,
                start_date=exp.start_date,
                end_date=exp.end_date,
                description=exp.description,
                source=DataSource.parsed,
            )
        )

    skills = get_or_create_skills(db, skill_names)
    existing_links = {
        cs.skill_id
        for cs in db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id == candidate_id
        )
    }
    for skill in skills:
        if skill.skill_id in existing_links:
            continue
        db.add(
            CandidateSkill(
                candidate_id=candidate_id,
                skill_id=skill.skill_id,
                resume_id=resume_id,
                source=DataSource.parsed,
            )
        )

    db.commit()
