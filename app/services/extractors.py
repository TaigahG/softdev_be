"""File → plain-text extraction.

Branches on file_type; LLM parser consumes the resulting string.
"""
import io


class UnsupportedFileType(ValueError):
    pass


def extract_text(content: bytes, file_type: str) -> str:
    ft = file_type.lower()
    if ft == "pdf":
        return _extract_pdf(content)
    if ft == "docx":
        return _extract_docx(content)
    raise UnsupportedFileType(f"unsupported file_type: {file_type!r}")


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs).strip()
