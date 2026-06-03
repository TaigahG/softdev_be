from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Skill


def get_or_create_skills(db: Session, names: Iterable[str]) -> list[Skill]:
    """Resolve skill names to Skill rows, creating missing ones.

    Names are lowercased + trimmed so 'Python', ' python ', and 'PYTHON'
    dedupe to a single row. Caller is responsible for the commit — this
    function only flushes so newly created IDs are populated.
    """
    normalized = {n.strip().lower() for n in names if n and n.strip()}
    if not normalized:
        return []

    existing = db.query(Skill).filter(Skill.skill_name.in_(normalized)).all()
    existing_by_name = {s.skill_name: s for s in existing}

    new_skills = [
        Skill(skill_name=n) for n in normalized if n not in existing_by_name
    ]
    if new_skills:
        db.add_all(new_skills)
        db.flush()

    return list(existing_by_name.values()) + new_skills


def search(db: Session, query: str, limit: int = 20) -> list[Skill]:
    """ILIKE prefix match for the frontend's TagInput autocomplete."""
    q = (query or "").strip().lower()
    if not q:
        return []
    return (
        db.query(Skill)
        .filter(Skill.skill_name.ilike(f"{q}%"))
        .order_by(Skill.skill_name)
        .limit(limit)
        .all()
    )
