"""Smoke tests for recommendation scoring + endpoints."""
from types import SimpleNamespace


# ────────────────────────── pure scoring tests ──────────────────────────


def _skill(skill_id, name="x"):
    return SimpleNamespace(skill_id=skill_id, skill_name=name)


def _candidate(**kw):
    return SimpleNamespace(
        candidate_id=1,
        skills=kw.pop("skills", []),
        preferred_working_mode=kw.pop("preferred_working_mode", None),
        preferred_location=kw.pop("preferred_location", None),
        years_of_experience=kw.pop("years_of_experience", None),
        education_level=kw.pop("education_level", None),
        **kw,
    )


def _job(**kw):
    return SimpleNamespace(
        job_id=1,
        required_skills=kw.pop("required_skills", []),
        work_mode=kw.pop("work_mode", None),
        location=kw.pop("location", None),
        required_experience=kw.pop("required_experience", None),
        required_education=kw.pop("required_education", None),
        **kw,
    )


def test_perfect_match_scores_100():
    """All five dimensions align → max score."""
    from app.services.scoring import score_match

    skills = [_skill(1, "python"), _skill(2, "fastapi")]
    candidate = _candidate(
        skills=skills,
        preferred_working_mode="remote",
        preferred_location="Bali",
        years_of_experience="3-5",
        education_level="bachelor",
    )
    job = _job(
        required_skills=skills,
        work_mode="remote",
        location="Bali",
        required_experience=3,
        required_education="bachelor",
    )
    assert score_match(candidate, job) == 100.0


def test_zero_skill_overlap_caps_score_at_40():
    """No skills matching = 0% of the 60-pt skill component. Other dims
    contribute 40 max."""
    from app.services.scoring import score_match

    candidate = _candidate(
        skills=[_skill(99, "haskell")],
        preferred_working_mode="remote",
        preferred_location="Bali",
        years_of_experience="3-5",
        education_level="bachelor",
    )
    job = _job(
        required_skills=[_skill(1, "python"), _skill(2, "fastapi")],
        work_mode="remote",
        location="Bali",
        required_experience=3,
        required_education="bachelor",
    )
    score = score_match(candidate, job)
    assert 39.0 < score < 41.0  # = 0 + 15 + 10 + 10 + 5


def test_null_fields_get_neutral_credit():
    """Missing optional fields don't penalise (half-credit on that dim)."""
    from app.services.scoring import score_match

    candidate = _candidate(skills=[_skill(1)])
    job = _job(required_skills=[_skill(1)])
    # 60 (perfect skill) + 7.5 + 5 + 5 + 2.5 = 80
    assert score_match(candidate, job) == 80.0


def test_higher_education_meets_requirement():
    """A master should satisfy a bachelor requirement."""
    from app.services.scoring import score_match

    cand = _candidate(education_level="master")
    job = _job(required_education="bachelor")
    # Half-credit on every other dim + full on education
    assert score_match(cand, job) > score_match(
        _candidate(education_level="high-school"), job
    )


def test_experience_bucket_covers_required_years():
    """Candidate's bucket '5-10' should cover a job requiring 5 years."""
    from app.services.scoring import score_match

    cand = _candidate(years_of_experience="5-10")
    job = _job(required_experience=5)
    assert score_match(cand, job) > score_match(
        _candidate(years_of_experience="0-1"), job
    )


# ──────────────────────── endpoint wiring tests ─────────────────────────


def test_candidate_recommendation_returns_cap_10_when_not_member(
    client, monkeypatch
):
    from app.crud import membership as crud_membership
    from app.crud import recommendation as crud_reco

    # Not a member → cap 10
    monkeypatch.setattr(crud_membership, "is_active_member", lambda db, uid: False)
    monkeypatch.setattr(
        crud_reco,
        "recommend_jobs_for_candidate",
        lambda db, candidate, is_member: [],
    )
    response = client.get("/candidates/me/recommended-jobs")
    assert response.status_code == 200
    assert response.json()["is_member"] is False


def test_candidate_recommendation_is_member_when_active(client, monkeypatch):
    from app.crud import membership as crud_membership
    from app.crud import recommendation as crud_reco

    monkeypatch.setattr(crud_membership, "is_active_member", lambda db, uid: True)
    monkeypatch.setattr(
        crud_reco,
        "recommend_jobs_for_candidate",
        lambda db, candidate, is_member: [],
    )
    response = client.get("/candidates/me/recommended-jobs")
    assert response.status_code == 200
    assert response.json()["is_member"] is True


def test_employer_recommendation_404_on_unknown_job(client, monkeypatch):
    from app.crud import job_posting as crud_job

    monkeypatch.setattr(crud_job, "get", lambda db, jid: None)
    response = client.get("/job-postings/999/recommended-candidates")
    assert response.status_code == 404
