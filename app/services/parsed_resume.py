"""Shape of an LLM-parsed resume.

This is the contract the parser produces and crud consumes. Kept separate
from app.schemas (HTTP layer) and app.models (DB layer) because it's the
internal hand-off between text extraction and persistence.

Education is now flat on the candidate (single entry — see DB schema change
notes); the parser proposes values and crud only writes them if the
candidate's columns are still empty.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ParsedWorkExperience(BaseModel):
    company_name: str
    job_title: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class ParsedResume(BaseModel):
    # Flat education — populated onto candidates.education_level /
    # candidates.field_of_study by crud, only if those columns are NULL.
    education_level: Optional[str] = None
    field_of_study: Optional[str] = None
    work_experiences: list[ParsedWorkExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
