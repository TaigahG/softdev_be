import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from pathlib import Path

import httpx
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models import Employer
from app.schemas import JobPostingCreate, JobStatus, WorkingMode
from app.crud import job_posting as job_posting_crud
from app.services import storage

EMPLOYER_COUNT = 20
JOB_COUNT = 150

COMPANY_PREFIX = os.getenv("SEED_COMPANY_PREFIX", "SeedCo")
DEFAULT_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD", "SeedPassword!123")
FORCE = os.getenv("SEED_FORCE", "0") == "1"
EMAIL_PREFIX = os.getenv("SEED_EMAIL_PREFIX", "seed-employer")
EMAIL_SUFFIX = os.getenv("SEED_EMAIL_SUFFIX", "")

IMAGE_WIDTH = 800
IMAGE_HEIGHT = 500

JOB_TITLES = [
    "Software Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Developer",
    "Data Analyst",
    "Data Scientist",
    "Product Manager",
    "UX Designer",
    "DevOps Engineer",
    "QA Engineer",
    "Mobile Developer",
    "Cloud Engineer",
    "Site Reliability Engineer",
    "Security Engineer",
    "Machine Learning Engineer",
    "Technical Writer",
    "Business Analyst",
    "Sales Engineer",
    "Customer Success Manager",
    "Solutions Architect",
]

LOCATIONS = [
    "Singapore",
    "Jakarta",
    "Kuala Lumpur",
    "Bangkok",
    "Manila",
    "Ho Chi Minh City",
    "Tokyo",
    "Seoul",
    "Sydney",
    "Melbourne",
    "Remote",
]

COMPANY_TAGLINES = [
    "Building tools that make teams faster.",
    "We help businesses scale with reliable software.",
    "A modern platform for hiring at scale.",
    "Design-first approach to delightful products.",
    "Data-driven solutions for everyday problems.",
    "Empowering creators with simple, elegant tech.",
]

SKILL_POOL = [
    "python",
    "typescript",
    "react",
    "next.js",
    "fastapi",
    "postgres",
    "docker",
    "aws",
    "gcp",
    "kubernetes",
    "graphql",
    "redis",
    "node.js",
    "sql",
    "terraform",
    "figma",
    "pandas",
    "numpy",
    "javascript",
    "tailwind",
    "django",
    "go",
    "rust",
    "java",
]


def _random_phone() -> str:
    return f"+65 8{random.randint(100, 999)} {random.randint(1000, 9999)}"


def _salary_range() -> str:
    low = random.randint(3, 8) * 1000
    high = low + random.randint(2, 8) * 1000
    return f"${low:,} - ${high:,}"


def _random_skills() -> list[str]:
    return random.sample(SKILL_POOL, k=random.randint(3, 6))


def _download_image(seed: str) -> tuple[bytes, str, str]:
    url = f"https://picsum.photos/seed/{seed}/{IMAGE_WIDTH}/{IMAGE_HEIGHT}"
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg")
    filename = f"{seed}.jpg"
    return response.content, filename, content_type


@dataclass
class SeededEmployer:
    employer_id: int
    user_id: UUID
    company_name: str


def _create_supabase_user(email: str, password: str) -> UUID:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")

    client = create_client(url, key)
    result = client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"role": "employer"},
        }
    )

    user = getattr(result, "user", None) or result.get("user")
    if not user:
        raise RuntimeError("Failed to create user in Supabase Auth.")
    user_id = getattr(user, "id", None) or user.get("id")
    if not user_id:
        raise RuntimeError("Supabase user id missing from response.")
    return UUID(str(user_id))


def _should_abort_if_seeded(db) -> None:
    existing = (
        db.query(Employer)
        .filter(Employer.company_name.ilike(f"{COMPANY_PREFIX}%"))
        .count()
    )
    if existing > 0 and not FORCE:
        raise RuntimeError(
            f"Found {existing} existing seeded employers with prefix '{COMPANY_PREFIX}'. "
            "Set SEED_FORCE=1 to re-run."
        )


def _job_distribution(total_jobs: int, employers: int) -> list[int]:
    base = total_jobs // employers
    remainder = total_jobs - (base * employers)
    counts = [base] * employers
    # Keep within 7-10 by ensuring base is 7 or 8 for 150/20.
    for idx in random.sample(range(employers), remainder):
        counts[idx] += 1
    return counts


def main() -> None:
    random.seed(42)

    if EMPLOYER_COUNT <= 0 or JOB_COUNT <= 0:
        raise RuntimeError("EMPLOYER_COUNT and JOB_COUNT must be positive.")

    db = SessionLocal()
    try:
        _should_abort_if_seeded(db)

        job_counts = _job_distribution(JOB_COUNT, EMPLOYER_COUNT)
        seeded_employers: list[SeededEmployer] = []

        for i in range(EMPLOYER_COUNT):
            company_number = i + 1
            company_name = f"{COMPANY_PREFIX} {company_number:02d}"
            suffix = f"-{EMAIL_SUFFIX}" if EMAIL_SUFFIX else ""
            email = f"{EMAIL_PREFIX}-{company_number:02d}{suffix}@seed.example"

            user_id = _create_supabase_user(email, DEFAULT_PASSWORD)

            company_seed = f"company-{company_number:02d}"
            profile_seed = f"profile-{company_number:02d}"

            company_bytes, company_filename, company_type = _download_image(company_seed)
            profile_bytes, profile_filename, profile_type = _download_image(profile_seed)

            company_picture = storage.upload(
                storage.images_bucket(), company_filename, company_bytes, company_type
            )
            profile_picture = storage.upload(
                storage.images_bucket(), profile_filename, profile_bytes, profile_type
            )

            existing_employer = (
                db.query(Employer)
                .filter(Employer.user_id == user_id)
                .first()
            )
            if existing_employer:
                seeded_employers.append(
                    SeededEmployer(
                        employer_id=existing_employer.employer_id,
                        user_id=user_id,
                        company_name=company_name,
                    )
                )
                continue

            employer = Employer(
                user_id=user_id,
                full_name=f"Recruiter {company_number:02d}",
                company_name=company_name,
                phone_number=_random_phone(),
                company_information=random.choice(COMPANY_TAGLINES),
                company_website=f"https://{company_name.replace(' ', '').lower()}.com",
                profile_picture=profile_picture,
                company_picture=company_picture,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(employer)
            db.flush()

            seeded_employers.append(
                SeededEmployer(
                    employer_id=employer.employer_id,
                    user_id=user_id,
                    company_name=company_name,
                )
            )

        db.commit()

        for employer, job_count in zip(seeded_employers, job_counts, strict=True):
            for _ in range(job_count):
                title = random.choice(JOB_TITLES)
                job = JobPostingCreate(
                    title=title,
                    company_info=f"{employer.company_name} - {random.choice(COMPANY_TAGLINES)}",
                    required_education=random.choice(
                        [
                            "high-school",
                            "associate",
                            "bachelor",
                            "master",
                            "doctorate",
                        ]
                    ),
                    required_experience=random.randint(0, 10),
                    work_mode=random.choice(list(WorkingMode)),
                    location=random.choice(LOCATIONS),
                    salary_range=_salary_range(),
                    status=JobStatus.published,
                    required_skills=_random_skills(),
                )
                job_posting_crud.create(
                    db, employer_id=employer.employer_id, data=job
                )

        print(
            f"Seeded {EMPLOYER_COUNT} employers and {JOB_COUNT} jobs. "
            f"Default password: {DEFAULT_PASSWORD}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
