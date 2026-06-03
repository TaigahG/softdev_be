from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.schemas import (
    ApplicationStatus,
    DataSource,
    JobStatus,
    ParseStatus,
    WorkingMode,
)

# Users are owned by Supabase Auth (auth.users, UUID PK). We FK to it from
# candidate/employer/membership rows; we don't manage a public.users table.
# This stub lets SQLAlchemy resolve the FK. create_all() uses checkfirst=True
# by default, so it won't try to recreate auth.users on Supabase (which already
# provisions it). For Alembic, exclude tables with schema='auth' in env.py.
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
)
AUTH_USER_FK = "auth.users.id"


class Membership(Base):
    __tablename__ = "memberships"

    membership_id = Column(Integer, primary_key=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(AUTH_USER_FK, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Stripe tracking. customer_id is set on first checkout (before payment);
    # subscription_id + dates land via webhook after payment succeeds.
    stripe_customer_id = Column(String, nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(
        String, nullable=True, unique=True, index=True
    )
    status = Column(String, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(Integer, primary_key=True)
    skill_name = Column(String, unique=True, nullable=False, index=True)


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(AUTH_USER_FK, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name = Column(String(255), nullable=False)
    # Step-1 personal
    phone_number = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String(100), nullable=True)
    marital_status = Column(String(30), nullable=True)
    website = Column(String(255), nullable=True)
    biography = Column(Text, nullable=True)
    # Step-1 professional — years_of_experience is a bucket string ("0-1" etc.)
    years_of_experience = Column(String(20), nullable=True)
    candidate_level = Column(String(30), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    # Step-2 education — flat, single entry (replaces the dropped educations table)
    education_level = Column(String(50), nullable=True)
    field_of_study = Column(String(255), nullable=True)
    # Preferences
    preferred_working_mode = Column(Enum(WorkingMode), nullable=True)
    preferred_location = Column(String, nullable=True)
    # Timestamps — server_default so raw-SQL inserts (e.g. the auth trigger)
    # also get a value; Python onupdate covers SQLAlchemy UPDATEs.
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    resumes = relationship(
        "Resume", back_populates="candidate", cascade="all, delete-orphan"
    )
    work_experiences = relationship(
        "WorkExperience", back_populates="candidate", cascade="all, delete-orphan"
    )
    candidate_skills = relationship(
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan"
    )
    skills = relationship("Skill", secondary="candidate_skills", viewonly=True)
    applications = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"

    resume_id = Column(Integer, primary_key=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    parse_status = Column(
        Enum(ParseStatus), nullable=False, default=ParseStatus.pending
    )

    candidate = relationship("Candidate", back_populates="resumes")
    work_experiences = relationship("WorkExperience", back_populates="resume")
    candidate_skills = relationship("CandidateSkill", back_populates="resume")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    experience_id = Column(Integer, primary_key=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id = Column(
        Integer,
        ForeignKey("resumes.resume_id", ondelete="SET NULL"),
        nullable=True,
    )
    company_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    source = Column(Enum(DataSource), nullable=False, default=DataSource.manual)

    candidate = relationship("Candidate", back_populates="work_experiences")
    resume = relationship("Resume", back_populates="work_experiences")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        primary_key=True,
    )
    resume_id = Column(
        Integer,
        ForeignKey("resumes.resume_id", ondelete="SET NULL"),
        nullable=True,
    )
    source = Column(Enum(DataSource), nullable=False, default=DataSource.manual)

    candidate = relationship("Candidate", back_populates="candidate_skills")
    skill = relationship("Skill")
    resume = relationship("Resume", back_populates="candidate_skills")


class Employer(Base):
    __tablename__ = "employers"

    employer_id = Column(Integer, primary_key=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(AUTH_USER_FK, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)
    company_information = Column(Text, nullable=True)
    company_website = Column(String(255), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    company_picture = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    job_postings = relationship(
        "JobPosting", back_populates="employer", cascade="all, delete-orphan"
    )


class JobPosting(Base):
    __tablename__ = "job_postings"

    job_id = Column(Integer, primary_key=True)
    employer_id = Column(
        Integer,
        ForeignKey("employers.employer_id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String, nullable=False)
    company_info = Column(Text, nullable=True)
    required_education = Column(String, nullable=True)
    required_experience = Column(Integer, nullable=True)
    work_mode = Column(Enum(WorkingMode), nullable=True)
    location = Column(String, nullable=True)
    salary_range = Column(String, nullable=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.draft)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    employer = relationship("Employer", back_populates="job_postings")
    job_skills = relationship(
        "JobSkill", back_populates="job", cascade="all, delete-orphan"
    )
    required_skills = relationship("Skill", secondary="job_skills", viewonly=True)
    applications = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id = Column(
        Integer,
        ForeignKey("job_postings.job_id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        primary_key=True,
    )

    job = relationship("JobPosting", back_populates="job_skills")
    skill = relationship("Skill")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "job_id", name="uq_application_candidate_job"
        ),
    )

    application_id = Column(Integer, primary_key=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        Integer,
        ForeignKey("job_postings.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    applied_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(
        Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.pending
    )
    cover_letter = Column(Text, nullable=True)

    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("JobPosting", back_populates="applications")
