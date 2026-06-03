"""Resume parsing pipeline.

State machine:
    POST /resumes
        → INSERT Resume(parse_status='pending'), return 201 immediately.
    BackgroundTasks → run_parse(resume_id)
        → download file → extract text → extract_structured(text) [LLM]
          → crud.insert_parsed_children → mark_status('success')
        → on any exception: mark_status('failed') and log.

Plug-in point:
    extract_structured() — replace the stub with a real Claude API call.
"""
import logging

from anthropic import Anthropic

from app.crud import resume as crud_resume
from app.database import SessionLocal
from app.schemas import ParseStatus
from app.services import extractors, storage
from app.services.parsed_resume import ParsedResume

log = logging.getLogger(__name__)


def run_parse(resume_id: int) -> None:
    """Entry point for BackgroundTasks. Opens its own DB session."""
    db = SessionLocal()
    try:
        resume = crud_resume.get(db, resume_id)
        if resume is None:
            log.warning("resume %s vanished before parse", resume_id)
            return

        try:
            content = storage.download(resume.file_url)
            text = extractors.extract_text(content, resume.file_type)
            parsed = extract_structured(text)

            crud_resume.insert_parsed_children(
                db,
                resume_id=resume.resume_id,
                candidate_id=resume.candidate_id,
                education_level=parsed.education_level,
                field_of_study=parsed.field_of_study,
                work_experiences=parsed.work_experiences,
                skill_names=parsed.skills,
            )
            crud_resume.mark_status(db, resume_id, ParseStatus.success)
        except Exception:
            log.exception("resume %s parse failed", resume_id)
            crud_resume.mark_status(db, resume_id, ParseStatus.failed)
    finally:
        db.close()


_SYSTEM_PROMPT = (
    "Extract structured data from resume text. Only include what is "
    "explicitly stated — do not invent details.\n\n"
    "Education: return ONE highest-attained entry (single education_level + "
    "field_of_study) — not a list. education_level MUST be exactly one of: "
    "high-school, associate, bachelor, master, doctorate (lowercase, "
    "hyphenated). If education isn't mentioned, use null for both fields.\n\n"
    "Work experience: extract every role. For dates use ISO YYYY-MM-DD; if "
    "only a year or month is given, use the first day of that period. Use "
    "null for missing dates. If company_name or job_title isn't stated, use "
    "an empty string rather than dropping the entry.\n\n"
    "Skills: list each skill as a string with conventional casing "
    "(e.g. 'JavaScript', 'PostgreSQL', 'AWS')."
)


def extract_structured(text: str) -> ParsedResume:
    """Parse resume text into structured fields via Claude.

    Empty input short-circuits to an empty ParsedResume without an API call.
    On API or validation error, raises — run_parse() catches and marks the
    resume failed.
    """
    if not text.strip():
        return ParsedResume()

    client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.parse(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        output_format=ParsedResume,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract education, work experience, and skills from "
                    f"this resume:\n\n{text}"
                ),
            }
        ],
    )
    return response.parsed_output
