"""
Seed 60 candidates with diverse profiles, skills, and work experiences.

Usage:
    python scripts/seed_candidates.py

Env vars:
    SEED_CANDIDATE_PREFIX   prefix for company name check  (default: SeedCandidate)
    SEED_DEFAULT_PASSWORD   password for all seeded users  (default: SeedPassword!123)
    SEED_FORCE              set to 1 to re-seed even if candidates exist
    SEED_EMAIL_SUFFIX       optional suffix on email addresses
"""

import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models import Candidate, CandidateSkill, WorkExperience
from app.crud.skill import get_or_create_skills
from app.schemas import DataSource, WorkingMode

CANDIDATE_COUNT = 60
CANDIDATE_PREFIX = os.getenv("SEED_CANDIDATE_PREFIX", "SeedCandidate")
DEFAULT_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD", "SeedPassword!123")
FORCE = os.getenv("SEED_FORCE", "0") == "1"
EMAIL_PREFIX = os.getenv("SEED_EMAIL_PREFIX", "seed-candidate")
EMAIL_SUFFIX = os.getenv("SEED_EMAIL_SUFFIX", "")

IMAGE_WIDTH = 400
IMAGE_HEIGHT = 400

# ── Candidate name pool ───────────────────────────────────────────────────────

FIRST_NAMES = [
    # Southeast Asian
    "Andi", "Budi", "Citra", "Dewi", "Eko", "Fajar", "Gita", "Hendra",
    "Indah", "Joko", "Kevin", "Lina", "Marco", "Nurul", "Omar",
    "Putri", "Rizky", "Sari", "Taufik", "Ulfa",
    # East Asian
    "Wei", "Xin", "Yuki", "Zhen", "Min", "Jia", "Hana", "Ren",
    # South Asian
    "Arjun", "Priya", "Rahul", "Sneha", "Vikram", "Ananya",
    # Western
    "Alex", "Blake", "Casey", "Dana", "Evan", "Frances",
    "Jordan", "Morgan", "Riley", "Taylor",
    # Filipino
    "Jasmine", "Carlo", "Maria", "Jose", "Ana",
]

LAST_NAMES = [
    "Santoso", "Wijaya", "Kusuma", "Pratama", "Setiawan",
    "Tan", "Wong", "Lim", "Chen", "Lee",
    "Sharma", "Patel", "Kumar", "Singh", "Nair",
    "Santos", "Reyes", "Cruz", "Bautista", "Garcia",
    "Smith", "Johnson", "Williams", "Brown", "Davis",
    "Nguyen", "Tran", "Pham", "Le", "Hoang",
    "Kim", "Park", "Choi", "Yoon", "Jung",
    "Sato", "Yamamoto", "Nakamura", "Kobayashi", "Ito",
]

NATIONALITIES = [
    "Indonesian", "Singaporean", "Malaysian", "Filipino", "Vietnamese",
    "Thai", "Australian", "Japanese", "South Korean", "Indian",
    "American", "British", "Chinese",
]

CITY_LOCATIONS = [
    "Singapore", "Jakarta", "Kuala Lumpur", "Bangkok", "Manila",
    "Ho Chi Minh City", "Tokyo", "Seoul", "Sydney", "Melbourne",
    "Mumbai", "New Delhi", "London", "New York", "Remote",
]

GENDERS = ["male", "female", "other", "prefer-not-to-say"]
MARITAL_STATUSES = ["single", "married", "divorced", "widowed"]
CANDIDATE_LEVELS = ["entry", "mid", "expert"]
YEARS_OF_EXPERIENCE = ["0-1", "1-3", "3-5", "5-10", "10+"]
EDUCATION_LEVELS = ["high-school", "associate", "bachelor", "master", "doctorate"]

FIELDS_OF_STUDY = [
    "Computer Science", "Software Engineering", "Information Systems",
    "Data Science", "Electrical Engineering", "Business Administration",
    "Mathematics", "Statistics", "Cybersecurity", "UX Design",
    "Product Management", "Graphic Design", "Finance", "Marketing",
    "Mechanical Engineering",
]

BIOGRAPHIES = [
    "Passionate software engineer with a love for building scalable web applications and clean APIs.",
    "Data-driven analyst who turns messy datasets into clear business insights.",
    "Creative UX designer focused on accessible, user-centered digital experiences.",
    "Full-stack developer with a background in fintech and a keen eye for performance optimization.",
    "DevOps enthusiast who enjoys automating everything and shipping fast.",
    "Mobile developer specializing in cross-platform apps with delightful UIs.",
    "Backend engineer experienced in high-traffic distributed systems and microservices.",
    "Machine learning engineer applying NLP and computer vision to real-world problems.",
    "Product manager bridging the gap between business goals and technical execution.",
    "Security-focused engineer passionate about building systems that don't get breached.",
    "Cloud architect with deep AWS and GCP experience, cost-optimization obsessed.",
    "Frontend specialist who cares deeply about accessibility and pixel-perfect designs.",
    "Versatile engineer who thrives in early-stage startups and fast-moving teams.",
    "QA engineer who believes quality is everyone's responsibility, not an afterthought.",
    "Technical writer who makes complex systems understandable for developers and users alike.",
]

SKILL_POOL = [
    "python", "typescript", "react", "next.js", "fastapi",
    "postgres", "docker", "aws", "gcp", "kubernetes",
    "graphql", "redis", "node.js", "sql", "terraform",
    "figma", "pandas", "numpy", "javascript", "tailwind",
    "django", "go", "rust", "java", "swift",
    "flutter", "pytorch", "tensorflow", "scikit-learn", "spark",
    "kafka", "elasticsearch", "mongodb", "mysql", "linux",
    "git", "ci/cd", "agile", "scrum", "jira",
]

# ── Work experience data pools ────────────────────────────────────────────────

COMPANIES = [
    "Tokopedia", "Gojek", "Grab", "Sea Group", "Bukalapak",
    "Traveloka", "OVO", "Dana", "Shopee", "Lazada",
    "Accenture", "IBM", "Deloitte", "ThoughtWorks", "Infosys",
    "Google", "Meta", "Microsoft", "Amazon", "Stripe",
    "Startup Labs", "ByteDance", "Alibaba", "Tencent", "Rakuten",
    "ANZ Bank", "DBS", "OCBC", "Maybank", "BCA",
    "Freelance", "Remote Agency", "Tech Bootcamp",
]

JOB_TITLES = [
    "Software Engineer", "Backend Engineer", "Frontend Engineer",
    "Full Stack Developer", "Data Analyst", "Data Scientist",
    "Product Manager", "UX Designer", "DevOps Engineer", "QA Engineer",
    "Mobile Developer", "Cloud Engineer", "Site Reliability Engineer",
    "Security Engineer", "Machine Learning Engineer", "Technical Writer",
    "Business Analyst", "Solutions Architect", "Junior Developer",
    "Senior Software Engineer", "Lead Engineer", "Engineering Manager",
    "Data Engineer", "Platform Engineer", "Research Engineer",
]

WORK_DESCRIPTIONS = [
    "Built and maintained RESTful APIs serving millions of requests per day.",
    "Led frontend development using React and TypeScript, improving page load by 40%.",
    "Designed and implemented data pipelines processing 500GB of daily logs.",
    "Collaborated with cross-functional teams to deliver features on a two-week sprint cycle.",
    "Migrated legacy monolith to microservices architecture on Kubernetes.",
    "Conducted user research and designed wireframes for a redesigned onboarding flow.",
    "Automated CI/CD pipelines reducing deployment time from 2 hours to 15 minutes.",
    "Built machine learning models for churn prediction with 82% accuracy.",
    "Wrote technical documentation and API guides used by 200+ external developers.",
    "Managed a team of 5 engineers, conducting weekly 1-on-1s and sprint planning.",
    "Optimized SQL queries reducing dashboard load time from 8s to under 1s.",
    "Developed mobile app features for iOS and Android using Flutter.",
    "Implemented OAuth2 and JWT authentication across multiple services.",
    "Performed penetration testing and resolved critical security vulnerabilities.",
    "Created A/B testing framework that increased conversion rate by 12%.",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _random_phone() -> str:
    return f"+65 8{random.randint(100, 999)} {random.randint(1000, 9999)}"


def _random_dob(level: str) -> date:
    if level == "entry":
        year = random.randint(1999, 2003)
    elif level == "mid":
        year = random.randint(1993, 1998)
    else:
        year = random.randint(1983, 1992)
    return date(year, random.randint(1, 12), random.randint(1, 28))


def _random_skills(n: int = None) -> list[str]:
    k = n or random.randint(3, 8)
    return random.sample(SKILL_POOL, k=k)


def _random_work_experiences(level: str, candidate_name: str) -> list[dict]:
    count = {"entry": 1, "mid": 2, "expert": 3}[level]
    exp_years = {"entry": "0-1", "mid": "1-3", "expert": "5-10"}[level]
    experiences = []
    year = 2024
    for i in range(count):
        duration = random.randint(1, 3)
        end_year = year - (i * duration)
        start_year = end_year - duration
        experiences.append({
            "company_name": random.choice(COMPANIES),
            "job_title": random.choice(JOB_TITLES),
            "start_date": date(start_year, random.randint(1, 6), 1),
            "end_date": date(end_year, random.randint(7, 12), 1) if i > 0 else None,
            "description": random.choice(WORK_DESCRIPTIONS),
        })
    return experiences


def _download_profile_picture(seed: str) -> tuple[bytes, str, str]:
    url = f"https://picsum.photos/seed/{seed}/{IMAGE_WIDTH}/{IMAGE_HEIGHT}"
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg")
    return response.content, f"{seed}.jpg", content_type


def _get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
    return create_client(url, key)


def _get_or_create_supabase_user(email: str, password: str) -> UUID:
    client = _get_supabase_client()
    try:
        result = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"role": "candidate"},
        })
        user = getattr(result, "user", None) or result.get("user")
        if user:
            user_id = getattr(user, "id", None) or user.get("id")
            if user_id:
                return UUID(str(user_id))
    except Exception:
        pass

    all_users = client.auth.admin.list_users()
    for u in all_users:
        if getattr(u, "email", None) == email:
            return UUID(str(u.id))
    raise RuntimeError(f"Could not find or create Supabase user for {email}")


def _should_abort_if_seeded(db) -> None:
    existing = (
        db.query(Candidate)
        .filter(Candidate.full_name.ilike(f"{CANDIDATE_PREFIX}%"))
        .count()
    )
    if existing > 0 and not FORCE:
        raise RuntimeError(
            f"Found {existing} existing seeded candidates with prefix '{CANDIDATE_PREFIX}'. "
            "Set SEED_FORCE=1 to re-run."
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    random.seed(99)

    db = SessionLocal()
    try:
        _should_abort_if_seeded(db)

        used_names: set[str] = set()
        seeded = 0

        for i in range(CANDIDATE_COUNT):
            number = i + 1
            suffix = f"-{EMAIL_SUFFIX}" if EMAIL_SUFFIX else ""
            email = f"{EMAIL_PREFIX}-{number:02d}{suffix}@seed.example"

            # Pick a unique full name
            for _ in range(50):
                full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                if full_name not in used_names:
                    used_names.add(full_name)
                    break

            level = random.choice(CANDIDATE_LEVELS)
            exp_bucket = {
                "entry": random.choice(["0-1", "1-3"]),
                "mid": random.choice(["1-3", "3-5"]),
                "expert": random.choice(["5-10", "10+"]),
            }[level]

            work_mode = random.choice(list(WorkingMode))
            preferred_location = (
                "Remote" if work_mode == WorkingMode.remote
                else random.choice(CITY_LOCATIONS)
            )

            user_id = _get_or_create_supabase_user(email, DEFAULT_PASSWORD)

            # Download profile picture
            try:
                pic_bytes, pic_filename, pic_type = _download_profile_picture(f"cand-{number:02d}")
                from app.services import storage
                profile_picture_url = storage.upload(
                    storage.images_bucket(), pic_filename, pic_bytes, pic_type
                )
            except Exception:
                profile_picture_url = None

            skills_names = _random_skills()
            skills = get_or_create_skills(db, skills_names)

            existing = (
                db.query(Candidate).filter(Candidate.user_id == user_id).first()
            )

            if existing:
                existing.full_name = full_name
                existing.phone_number = _random_phone()
                existing.gender = random.choice(GENDERS)
                existing.date_of_birth = _random_dob(level)
                existing.nationality = random.choice(NATIONALITIES)
                existing.marital_status = random.choice(MARITAL_STATUSES)
                existing.website = f"https://github.com/{full_name.lower().replace(' ', '-')}"
                existing.biography = random.choice(BIOGRAPHIES)
                existing.years_of_experience = exp_bucket
                existing.candidate_level = level
                existing.profile_picture = profile_picture_url
                existing.education_level = random.choice(EDUCATION_LEVELS)
                existing.field_of_study = random.choice(FIELDS_OF_STUDY)
                existing.preferred_working_mode = work_mode
                existing.preferred_location = preferred_location
                db.flush()
                candidate = existing
            else:
                candidate = Candidate(
                    user_id=user_id,
                    full_name=full_name,
                    phone_number=_random_phone(),
                    gender=random.choice(GENDERS),
                    date_of_birth=_random_dob(level),
                    nationality=random.choice(NATIONALITIES),
                    marital_status=random.choice(MARITAL_STATUSES),
                    website=f"https://github.com/{full_name.lower().replace(' ', '-')}",
                    biography=random.choice(BIOGRAPHIES),
                    years_of_experience=exp_bucket,
                    candidate_level=level,
                    profile_picture=profile_picture_url,
                    education_level=random.choice(EDUCATION_LEVELS),
                    field_of_study=random.choice(FIELDS_OF_STUDY),
                    preferred_working_mode=work_mode,
                    preferred_location=preferred_location,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(candidate)
                db.flush()

            # Replace skills
            db.query(CandidateSkill).filter(
                CandidateSkill.candidate_id == candidate.candidate_id
            ).delete(synchronize_session=False)
            db.flush()
            for skill in skills:
                db.add(CandidateSkill(
                    candidate_id=candidate.candidate_id,
                    skill_id=skill.skill_id,
                    source=DataSource.manual,
                    resume_id=None,
                ))

            # Add work experiences (clear old ones first)
            from app.models import WorkExperience as WE
            db.query(WE).filter(
                WE.candidate_id == candidate.candidate_id,
                WE.source == DataSource.manual,
            ).delete(synchronize_session=False)
            db.flush()

            for exp in _random_work_experiences(level, full_name):
                db.add(WE(
                    candidate_id=candidate.candidate_id,
                    resume_id=None,
                    company_name=exp["company_name"],
                    job_title=exp["job_title"],
                    start_date=exp["start_date"],
                    end_date=exp["end_date"],
                    description=exp["description"],
                    source=DataSource.manual,
                ))

            db.commit()
            seeded += 1
            print(f"[{seeded:02d}/{CANDIDATE_COUNT}] {full_name} ({level}, {exp_bucket} yrs, {work_mode.value})")

        print(f"\nDone. Seeded {seeded} candidates. Default password: {DEFAULT_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
