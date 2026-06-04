"""Rule-based recommendation scoring.

Score(candidate, job) = weighted sum of structured-field matches over the
existing schema. Pure function over loaded ORM rows — no SQL, no ML.

    skill_overlap     (60 pts)  — how many of the job's required skills the
                                  candidate has, as a ratio
    work_mode_match   (15 pts)  — preferred working mode aligns
    location_match    (10 pts)  — preferred location matches (case-insensitive)
    experience_match  (10 pts)  — candidate's experience-bucket covers the
                                  job's required_experience (years)
    education_match   ( 5 pts)  — candidate's education_level meets the job's
                                  required_education
    ---------------------------------
    Total max         100 pts

When a comparison can't be made (either side is null), a neutral half-credit
is awarded for that dimension. This avoids penalising candidates / jobs
that haven't filled every optional field.
"""
from typing import Optional

from app.models import Candidate, JobPosting

# ─────────────────────────────── helpers ────────────────────────────────

# Map bucket strings to (min, max) numeric ranges of years.
_EXPERIENCE_BUCKETS: dict[str, tuple[int, int]] = {
    "0-1": (0, 1),
    "1-3": (1, 3),
    "3-5": (3, 5),
    "5-10": (5, 10),
    "10+": (10, 999),
}

# Ordinal ranking for education levels — higher meets lower.
_EDUCATION_LEVEL_RANK: dict[str, int] = {
    "high-school": 1,
    "associate": 2,
    "bachelor": 3,
    "master": 4,
    "doctorate": 5,
}


def _bucket_max_years(bucket: Optional[str]) -> Optional[int]:
    if not bucket:
        return None
    rng = _EXPERIENCE_BUCKETS.get(bucket)
    return rng[1] if rng else None


def _education_rank(level: Optional[str]) -> Optional[int]:
    if not level:
        return None
    return _EDUCATION_LEVEL_RANK.get(level.lower())


# ─────────────────────────────── scoring ────────────────────────────────


def _skill_overlap(candidate: Candidate, job: JobPosting) -> float:
    """Returns a fraction in [0, 1] indicating how much of the job's required
    skill set the candidate possesses. Neutral 0.5 if the job has no required
    skills (we have no signal either way)."""
    job_skill_ids = {s.skill_id for s in job.required_skills}
    if not job_skill_ids:
        return 0.5
    candidate_skill_ids = {s.skill_id for s in candidate.skills}
    return len(candidate_skill_ids & job_skill_ids) / len(job_skill_ids)


def _work_mode_score(candidate: Candidate, job: JobPosting) -> float:
    if candidate.preferred_working_mode is None or job.work_mode is None:
        return 0.5
    return 1.0 if candidate.preferred_working_mode == job.work_mode else 0.0


def _location_score(candidate: Candidate, job: JobPosting) -> float:
    cand_loc = (candidate.preferred_location or "").strip().lower()
    job_loc = (job.location or "").strip().lower()
    if not cand_loc or not job_loc:
        return 0.5
    # Lenient substring match — "Bali" matches "Denpasar, Bali" or vice versa.
    return 1.0 if (cand_loc in job_loc or job_loc in cand_loc) else 0.0


def _experience_score(candidate: Candidate, job: JobPosting) -> float:
    if candidate.years_of_experience is None or job.required_experience is None:
        return 0.5
    cand_max = _bucket_max_years(candidate.years_of_experience)
    if cand_max is None:
        return 0.5
    # Candidate's bucket should cover the job's required years.
    return 1.0 if cand_max >= job.required_experience else 0.0


def _education_score(candidate: Candidate, job: JobPosting) -> float:
    if candidate.education_level is None or job.required_education is None:
        return 0.5
    cand_rank = _education_rank(candidate.education_level)
    req_rank = _education_rank(job.required_education)
    if cand_rank is None or req_rank is None:
        return 0.5
    return 1.0 if cand_rank >= req_rank else 0.0


def score_match(candidate: Candidate, job: JobPosting) -> float:
    """Total weighted score in [0, 100]. Higher = better fit."""
    return (
        60.0 * _skill_overlap(candidate, job)
        + 15.0 * _work_mode_score(candidate, job)
        + 10.0 * _location_score(candidate, job)
        + 10.0 * _experience_score(candidate, job)
        + 5.0 * _education_score(candidate, job)
    )
