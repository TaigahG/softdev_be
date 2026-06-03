from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crud import skill as crud_skill
from app.database import get_db
from app.schemas import SkillOut

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def search_skills(
    q: str = Query("", description="Prefix to match against skill names"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[SkillOut]:
    return crud_skill.search(db, q, limit=limit)
