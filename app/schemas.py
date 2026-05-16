from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    candidate = "candidate"
    employer = "employer"

class WorkingMode(str, Enum):
    remote = "remote"
    onsite = "onsite"
    hybrid = "hybrid"

class ParseStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"

class JobStatus(str, Enum):
    draft = "draft"
    published = "published"

class ApplicationStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"

class DataSource(str, Enum):
    parsed = "parsed"
    manual = "manual"


# User
class UserBase(BaseModel):
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    # User registration
    password: str

class UserOut(UserBase):
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Membership
class MembershipBase(BaseModel):
    is_active: bool
    start_date: date
    end_date: date

class MembershipCreate(MembershipBase):
    user_id: int

class MembershipOut(MembershipBase):
    membership_id: int
    user_id: int

    class Config:
        from_attributes = True


# Skills
class SkillBase(BaseModel):
    skill_name: str

class SkillCreate(SkillBase):
    pass

class SkillOut(SkillBase):
    skill_id: int

    class Config:
        from_attributes = True


# Resume / CV
class ResumeBase(BaseModel):
    file_name: str
    file_type: str  # pdf / docx

class ResumeCreate(ResumeBase):
    candidate_id: int
    file_url: str

class ResumeOut(ResumeBase):
    resume_id: int
    candidate_id: int
    file_url: str
    uploaded_at: datetime
    parse_status: ParseStatus

    class Config:
        from_attributes = True


# Education
class EducationBase(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class EducationCreate(EducationBase):
    candidate_id: int
    source: DataSource = DataSource.manual

class EducationOut(EducationBase):
    education_id: int
    candidate_id: int
    source: DataSource

    class Config:
        from_attributes = True


# Work Experiences
class WorkExperienceBase(BaseModel):
    company_name: str
    job_title: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

class WorkExperienceCreate(WorkExperienceBase):
    candidate_id: int
    resume_id: Optional[int] = None      # null if manually entered
    source: DataSource = DataSource.manual

class WorkExperienceOut(WorkExperienceBase):
    experience_id: int
    candidate_id: int
    resume_id: Optional[int]
    source: DataSource

    class Config:
        from_attributes = True


# Candidate
class CandidateBase(BaseModel):
    full_name: str
    contact_info: Optional[str] = None
    years_of_experience: Optional[int] = None
    preferred_working_mode: Optional[WorkingMode] = None
    preferred_location: Optional[str] = None

class CandidateCreate(CandidateBase):
    user_id: int

class CandidateUpdate(CandidateBase):
    # All fields optional for PATCH
    full_name: Optional[str] = None

class CandidateOut(CandidateBase):
    candidate_id: int
    user_id: int
    resume_url: Optional[str] = None
    skills: List[SkillOut] = []
    educations: List[EducationOut] = []
    work_experiences: List[WorkExperienceOut] = []

    class Config:
        from_attributes = True


# Candidate Skills
class CandidateSkillCreate(BaseModel):
    candidate_id: int
    skill_id: int
    resume_id: Optional[int] = None     # null if manually added
    source: DataSource = DataSource.manual

class CandidateSkillOut(BaseModel):
    candidate_id: int
    skill_id: int
    source: DataSource

    class Config:
        from_attributes = True


# Employer
class EmployerBase(BaseModel):
    full_name: str
    company_name: str

class EmployerCreate(EmployerBase):
    user_id: int

class EmployerUpdate(EmployerBase):
    full_name: Optional[str] = None
    company_name: Optional[str] = None

class EmployerOut(EmployerBase):
    employer_id: int
    user_id: int

    class Config:
        from_attributes = True


# Job Posting
class JobPostingBase(BaseModel):
    title: str
    company_info: Optional[str] = None
    required_education: Optional[str] = None
    required_experience: Optional[int] = None
    work_mode: Optional[WorkingMode] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None

class JobPostingCreate(JobPostingBase):
    employer_id: int
    status: JobStatus = JobStatus.draft

class JobPostingUpdate(JobPostingBase):
    # All fields optional for PATCH
    title: Optional[str] = None
    status: Optional[JobStatus] = None

class JobPostingOut(JobPostingBase):
    job_id: int
    employer_id: int
    status: JobStatus
    created_at: datetime
    required_skills: List[SkillOut] = []

    class Config:
        from_attributes = True


# Job Skills
class JobSkillCreate(BaseModel):
    job_id: int
    skill_id: int

class JobSkillOut(BaseModel):
    job_id: int
    skill_id: int

    class Config:
        from_attributes = True


# Application
class ApplicationBase(BaseModel):
    candidate_id: int
    job_id: int

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationOut(ApplicationBase):
    application_id: int
    applied_at: datetime
    status: ApplicationStatus
    candidate: Optional[CandidateOut] = None   # for employer view
    job: Optional[JobPostingOut] = None        # for candidate view

    class Config:
        from_attributes = True


# Search & Recommendation
class JobSearchQuery(BaseModel):
    # Supports keyword, filter, keyword+filter, fuzzy
    keyword: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[WorkingMode] = None
    salary_range: Optional[str] = None
    fuzzy: bool = False                        # enable fuzzy matching

class CandidateSearchQuery(BaseModel):
    keyword: Optional[str] = None
    preferred_location: Optional[str] = None
    working_mode: Optional[WorkingMode] = None
    required_experience: Optional[int] = None
    fuzzy: bool = False

class RecommendedJobsOut(BaseModel):
    # Unlimited for members, max 10 for non-members
    is_member: bool
    total: int
    jobs: List[JobPostingOut]

class RecommendedCandidatesOut(BaseModel):
    is_member: bool
    total: int
    candidates: List[CandidateOut]