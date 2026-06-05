"""Search queries — used by both /job-postings (public) and /candidates/search
(employer-only).

Modes per the project requirements:
  - Keyword only (FTS + synonym expansion)
  - Filter only (SQL WHERE)
  - Keyword + filter (FTS + WHERE)
  - Fuzzy (pg_trgm similarity, typo-tolerant)

The `fuzzy` flag is additive — it doesn't replace FTS, it complements it.
With fuzzy=True, we OR the trigram similarity match into the keyword clause so
typos like "sofware enginer" still hit jobs containing "software engineer".

Requires Supabase Postgres extension:
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

(One-time SQL Editor action — see README/setup notes.)
"""
import re
from typing import Optional

from sqlalchemy import Integer, cast, func, or_, text
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Candidate,
    Employer,
    JobPosting,
    JobSkill,
    Skill,
)
from app.schemas import JobStatus, WorkingMode
from app.services.synonyms import expand, to_tsquery_or

def _parse_salary_filter(salary_str: str) -> tuple[int, int | None]:
    """Parse a frontend salary filter string into (min, max) integers.

    Handles formats like '$4000 - $6000' and '$15000+'.
    Returns (min, None) for open-ended ranges.
    """
    s = salary_str.replace("$", "").replace(",", "").strip()
    if "+" in s:
        try:
            return int(s.replace("+", "").strip()), None
        except ValueError:
            return 0, None
    m = re.match(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, None


# Trigram word_similarity threshold for the fuzzy match (0.0-1.0).
# Lower = more permissive but more false-positives. 0.3 catches typos like
# "sofware enginer" → "software engineer" while filtering out junk.
# word_similarity is preferred over similarity here because we're matching a
# short query against a longer concatenated text — full-string similarity
# gets diluted by the surrounding context.
_TRGM_THRESHOLD = 0.3


# ─────────────────────────────── jobs ────────────────────────────────


def _job_text_column():
    """Concatenated text for FTS / trgm — title is the strongest signal."""
    return func.concat_ws(
        " ",
        func.coalesce(JobPosting.title, ""),
        func.coalesce(JobPosting.company_info, ""),
        func.coalesce(JobPosting.location, ""),
        func.coalesce(JobPosting.required_education, ""),
    )


def search_jobs(
    db: Session,
    *,
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    work_mode: Optional[WorkingMode] = None,
    salary_range: Optional[str] = None,
    status: Optional[JobStatus] = None,
    fuzzy: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[JobPosting], int]:
    """Public job search. Defaults status to 'published' so drafts never leak."""
    query = (
        db.query(JobPosting)
        .options(joinedload(JobPosting.required_skills))
        .filter(JobPosting.status == (status or JobStatus.published))
    )

    if keyword:
        expansions = expand(keyword)
        tsquery = to_tsquery_or(expansions)
        clauses = []

        # 1. FTS over concatenated job text — catches keyword + synonyms.
        text_col = _job_text_column()
        if tsquery:
            clauses.append(
                func.to_tsvector("english", text_col).op("@@")(
                    func.to_tsquery("english", tsquery)
                )
            )

        # 2. FTS hits via the required_skills join — synonyms applied here too.
        skill_subq = (
            db.query(JobSkill.job_id)
            .join(Skill, Skill.skill_id == JobSkill.skill_id)
            .filter(
                func.to_tsvector("english", Skill.skill_name).op("@@")(
                    func.to_tsquery("english", tsquery)
                )
            )
        )
        clauses.append(JobPosting.job_id.in_(skill_subq))

        # 3. (Optional) trigram fuzzy match — typo tolerance via pg_trgm.
        if fuzzy:
            clauses.append(
                func.word_similarity(keyword.lower(), text_col) > _TRGM_THRESHOLD
            )

        if clauses:
            query = query.filter(or_(*clauses))

    if location:
        query = query.filter(JobPosting.location.ilike(f"%{location}%"))
    if work_mode:
        query = query.filter(JobPosting.work_mode == work_mode)
    if salary_range:
        filter_min, filter_max = _parse_salary_filter(salary_range)
        # Extract the minimum salary number from the stored salary_range string.
        # e.g., "$4,000 - $11,000" → first capture group "4,000" → strip commas → cast to int.
        db_min = cast(
            func.regexp_replace(
                func.regexp_replace(
                    JobPosting.salary_range,
                    r'^[^0-9]*([0-9,]+).*$',
                    r'\1',
                ),
                r',',
                '',
                'g',
            ),
            Integer,
        )
        salary_clauses = [JobPosting.salary_range.op('~')(r'[0-9]')]
        if filter_max is None:
            salary_clauses.append(db_min >= filter_min)
        else:
            salary_clauses.append(db_min >= filter_min)
            salary_clauses.append(db_min <= filter_max)
        query = query.filter(*salary_clauses)

    total = query.with_entities(func.count(JobPosting.job_id.distinct())).scalar() or 0
    items = (
        query.order_by(JobPosting.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


# ─────────────────────────────── candidates ────────────────────────────


def _candidate_text_column():
    return func.concat_ws(
        " ",
        func.coalesce(Candidate.full_name, ""),
        func.coalesce(Candidate.biography, ""),
        func.coalesce(Candidate.field_of_study, ""),
        func.coalesce(Candidate.preferred_location, ""),
    )


def search_candidates(
    db: Session,
    *,
    keyword: Optional[str] = None,
    preferred_location: Optional[str] = None,
    working_mode: Optional[WorkingMode] = None,
    fuzzy: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Candidate], int]:
    """Employer-facing candidate search.

    Searches over candidate name, biography, field_of_study, preferred_location,
    and the candidate's skills (joined). Same fuzzy/synonym pipeline as jobs.
    """
    query = db.query(Candidate).options(
        joinedload(Candidate.skills),
        joinedload(Candidate.work_experiences),
    )

    if keyword:
        expansions = expand(keyword)
        tsquery = to_tsquery_or(expansions)
        clauses = []

        text_col = _candidate_text_column()
        if tsquery:
            clauses.append(
                func.to_tsvector("english", text_col).op("@@")(
                    func.to_tsquery("english", tsquery)
                )
            )

        # FTS over candidate skills (via candidate_skills join).
        from app.models import CandidateSkill
        skill_subq = (
            db.query(CandidateSkill.candidate_id)
            .join(Skill, Skill.skill_id == CandidateSkill.skill_id)
            .filter(
                func.to_tsvector("english", Skill.skill_name).op("@@")(
                    func.to_tsquery("english", tsquery)
                )
            )
        )
        clauses.append(Candidate.candidate_id.in_(skill_subq))

        if fuzzy:
            clauses.append(
                func.word_similarity(keyword.lower(), text_col) > _TRGM_THRESHOLD
            )

        if clauses:
            query = query.filter(or_(*clauses))

    if preferred_location:
        query = query.filter(
            Candidate.preferred_location.ilike(f"%{preferred_location}%")
        )
    if working_mode:
        query = query.filter(Candidate.preferred_working_mode == working_mode)

    total = (
        query.with_entities(func.count(Candidate.candidate_id.distinct())).scalar()
        or 0
    )
    items = (
        query.order_by(Candidate.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total
