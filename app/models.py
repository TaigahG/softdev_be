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
    Text,
)
from sqlalchemy.orm import relationship

from database import Base
from schemas import (
    ApplicationStatus,
    DataSource,
    JobStatus,
    ParseStatus,
    UserRole,
    WorkingMode,
)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(Enum(UserRole), nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    membership = relationship( 
        "Membership", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    candidate = relationship(
        "Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    employer = relationship(
        "Employer", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "memberships"

    membership_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    is_active = Column(Boolean, nullable=False, default=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    user = relationship("User", back_populates="membership")


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(Integer, primary_key=True)
    skill_name = Column(String, unique=True, nullable=False, index=True)


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name = Column(String, nullable=False)
    contact_info = Column(String, nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    preferred_working_mode = Column(Enum(WorkingMode), nullable=True)
    preferred_location = Column(String, nullable=True)

    user = relationship("User", back_populates="candidate")
    resumes = relationship(
        "Resume", back_populates="candidate", cascade="all, delete-orphan"
    )
    educations = relationship(
        "Education", back_populates="candidate", cascade="all, delete-orphan"
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


class Education(Base):
    __tablename__ = "educations"

    education_id = Column(Integer, primary_key=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field_of_study = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    source = Column(Enum(DataSource), nullable=False, default=DataSource.manual)

    candidate = relationship("Candidate", back_populates="educations")


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
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)

    user = relationship("User", back_populates="employer")
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

    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("JobPosting", back_populates="applications")
