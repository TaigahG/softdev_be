"""Sanity checks: app boots, all expected routes are registered, public
endpoints are reachable without auth."""

EXPECTED_PATHS = {
    # candidate
    "/candidates/search",
    "/candidates/me",
    "/candidates/me/resumes",
    "/candidates/me/profile-picture",
    "/candidates/me/work-experiences",
    "/candidates/me/recommended-jobs",
    "/candidates/{candidate_id}",
    # work experience
    "/work-experiences/{experience_id}",
    # employer
    "/employers/me",
    "/employers/me/profile-picture",
    "/employers/me/company-picture",
    "/employers/{employer_id}",
    # jobs
    "/job-postings",
    "/job-postings/{job_id}",
    "/job-postings/{job_id}/applications",
    "/job-postings/{job_id}/recommended-candidates",
    # applications
    "/applications",
    "/applications/me",
    "/applications/{application_id}",
    # resumes
    "/resumes",
    "/resumes/{resume_id}",
    # skills
    "/skills",
    # memberships
    "/memberships/checkout",
    "/memberships/me",
    "/memberships/portal",
    # health
    "/health",
    "/health/db",
}


def test_health(client):
    assert client.get("/health").status_code == 200


def test_all_routes_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"].keys())
    missing = EXPECTED_PATHS - paths
    assert not missing, f"missing routes: {missing}"
