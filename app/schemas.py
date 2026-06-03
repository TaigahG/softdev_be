from pydantic import BaseModel
from typing import Literal, Optional, List
from datetime import date, datetime
from enum import Enum
from uuid import UUID


# Constrained-string types — sourced from the frontend registration form.
# Stored as plain VARCHAR in the DB; validated here at the API boundary.
Gender = Literal["male", "female", "other", "prefer-not-to-say"]
MaritalStatus = Literal["single", "married", "divorced", "widowed"]
CandidateLevel = Literal["entry", "mid", "expert"]
EducationLevel = Literal[
    "high-school", "associate", "bachelor", "master", "doctorate"
]
YearsOfExperience = Literal["0-1", "1-3", "3-5", "5-10", "10+"]


# Enums
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


# Note: user identity is owned by Supabase Auth (auth.users, UUID PK).
# This service does not store users directly — candidate/employer/membership
# rows FK to auth.users.id by UUID. Profile fields live on those tables.


# Membership — Stripe-backed candidate subscription
class MembershipBase(BaseModel):
    is_active: bool = False
    status: Optional[str] = None              # mirrors Stripe sub status
    cancel_at_period_end: bool = False
    start_date: Optional[date] = None         # current period start
    end_date: Optional[date] = None           # current period end

class MembershipCreate(MembershipBase):
    user_id: UUID

class MembershipOut(MembershipBase):
    membership_id: Optional[int] = None       # None for synthetic "not a member" response
    user_id: UUID
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

    class Config:
        from_attributes = True

class MembershipCheckoutOut(BaseModel):
    url: str                                  # Stripe-hosted checkout URL

class MembershipPortalOut(BaseModel):
    url: str                                  # Stripe Customer Portal URL


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


# Work Experiences
class WorkExperienceBase(BaseModel):
    company_name: str
    job_title: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

class WorkExperienceCreate(WorkExperienceBase):
    # candidate_id is derived from auth, never accepted from the client
    resume_id: Optional[int] = None      # null if manually entered
    source: DataSource = DataSource.manual

class WorkExperienceUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

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
    # Step-1 personal fields
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    website: Optional[str] = None
    biography: Optional[str] = None
    # Step-1 professional fields
    years_of_experience: Optional[YearsOfExperience] = None
    candidate_level: Optional[CandidateLevel] = None
    profile_picture: Optional[str] = None
    # Step-2 education (flat, single entry — replaces the dropped educations table)
    education_level: Optional[EducationLevel] = None
    field_of_study: Optional[str] = None
    # Preferences (kept from prior schema)
    preferred_working_mode: Optional[WorkingMode] = None
    preferred_location: Optional[str] = None

class CandidateCreate(CandidateBase):
    user_id: UUID

class CandidateUpdate(CandidateBase):
    # All fields optional for PATCH
    full_name: Optional[str] = None
    # When provided, replaces ALL candidate_skills rows (parsed entries get wiped;
    # re-upload the resume to restore them). Source becomes 'manual'.
    skills: Optional[List[str]] = None

class CandidateOut(CandidateBase):
    candidate_id: int
    user_id: UUID
    resume_url: Optional[str] = None    # derived from latest Resume row
    skills: List[SkillOut] = []
    work_experiences: List[WorkExperienceOut] = []
    created_at: datetime
    updated_at: datetime

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
    phone_number: Optional[str] = None
    company_information: Optional[str] = None
    company_website: Optional[str] = None
    profile_picture: Optional[str] = None    # contact person avatar
    company_picture: Optional[str] = None    # company banner / logo

class EmployerCreate(EmployerBase):
    user_id: UUID

class EmployerUpdate(EmployerBase):
    full_name: Optional[str] = None
    company_name: Optional[str] = None

class EmployerOut(EmployerBase):
    employer_id: int
    user_id: UUID
    created_at: datetime
    updated_at: datetime

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
    # employer_id is derived from auth, never accepted from the client
    status: JobStatus = JobStatus.draft
    required_skills: Optional[List[str]] = None

class JobPostingUpdate(JobPostingBase):
    # All fields optional for PATCH
    title: Optional[str] = None
    status: Optional[JobStatus] = None
    required_skills: Optional[List[str]] = None

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
    cover_letter: Optional[str] = None   # submitted at apply time

class ApplicationUpdate(BaseModel):
    status: ApplicationStatus            # employer marks pending → reviewed

class ApplicationOut(ApplicationBase):
    application_id: int
    applied_at: datetime
    status: ApplicationStatus
    cover_letter: Optional[str] = None
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