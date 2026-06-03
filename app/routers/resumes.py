from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.crud import resume as crud_resume
from app.database import get_db
from app.models import Candidate
from app.schemas import ResumeOut
from app.services import storage
from app.services.auth import get_current_candidate
from app.services.resume_parser import run_parse

router = APIRouter(prefix="/resumes", tags=["resumes"])


_MIME_TO_FILE_TYPE = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def _resolve_file_type(upload: UploadFile) -> str:
    if upload.content_type in _MIME_TO_FILE_TYPE:
        return _MIME_TO_FILE_TYPE[upload.content_type]
    if upload.filename:
        ext = upload.filename.rsplit(".", 1)[-1].lower()
        if ext in {"pdf", "docx"}:
            return ext
    raise HTTPException(
        status_code=415,
        detail="Only PDF and DOCX resumes are supported.",
    )


@router.post("", response_model=ResumeOut, status_code=201)
def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> ResumeOut:
    file_type = _resolve_file_type(file)
    content = file.file.read()

    file_url = storage.upload_resume(
        filename=file.filename or f"resume.{file_type}",
        content=content,
        content_type=file.content_type or "application/octet-stream",
    )

    resume = crud_resume.create(
        db,
        candidate_id=candidate.candidate_id,
        file_name=file.filename or f"resume.{file_type}",
        file_type=file_type,
        file_url=file_url,
    )

    background_tasks.add_task(run_parse, resume.resume_id)
    return resume


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)) -> ResumeOut:
    resume = crud_resume.get(db, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="resume not found")
    return resume
