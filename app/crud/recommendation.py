"""Recommendation queries.

Loads candidates / jobs from the DB, scores in Python via app.services.scoring,
sorts, and applies the per-user-tier cap. Fine for the current data scale.
When the catalog grows to ~10k+ jobs, move to SQL-based ranking (CTE + ORDER BY
a computed score) — same scoring function, different layer.
"""
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models import Candidate, JobPosting
from app.schemas import JobStatus
from app.services.scoring import score_match

# Per-tier limits. Candidates pay for higher caps; employers always get the
# higher cap for v1 (no employer membership product yet).
FREE_CAP = 10
MEMBER_CAP: Optional[int] = None  # None = no cap


def recommend_jobs_for_candidate(
    db: Session,
    *,
    candidate: Candidate,
    is_member: bool,
) -> list[JobPosting]:
    """Score every published job against this candidate, return ranked list,
    capped at FREE_CAP if not a member."""
    jobs = (
        db.query(JobPosting)
        .options(joinedload(JobPosting.required_skills))
        .filter(JobPosting.status == JobStatus.published)
        .all()
    )
    ranked = sorted(
        jobs, key=lambda j: score_match(candidate, j), reverse=True
    )
    cap = MEMBER_CAP if is_member else FREE_CAP
    return ranked if cap is None else ranked[:cap]


def recommend_candidates_for_job(
    db: Session,
    *,
    job: JobPosting,
    cap: Optional[int] = None,
) -> list[Candidate]:
    """Score every candidate against this job, return ranked list. Employers
    have no membership gate in v1, so the default cap is None (unlimited)."""
    candidates = (
        db.query(Candidate)
        .options(
            joinedload(Candidate.skills),
            joinedload(Candidate.work_experiences),
        )
        .all()
    )
    ranked = sorted(
        candidates, key=lambda c: score_match(c, job), reverse=True
    )
    return ranked if cap is None else ranked[:cap]
