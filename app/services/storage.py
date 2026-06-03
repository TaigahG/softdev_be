"""Supabase Storage wrapper.

Requires env vars:
    SUPABASE_URL                — Project API URL (Project Settings → API)
    SUPABASE_SERVICE_ROLE_KEY   — Service-role key. SERVER-ONLY: bypasses RLS.
    RESUMES_BUCKET              — Resume bucket name, defaults to 'resumes'.
    IMAGES_BUCKET               — Image bucket name, defaults to 'images'.

Each bucket must be created once in the Supabase dashboard
(Storage → New bucket, mark Public for unsigned URLs).
"""
import os
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile, status
from supabase import Client, create_client

_client: Client | None = None

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
            )
        _client = create_client(url, key)
    return _client


def resumes_bucket() -> str:
    return os.getenv("RESUMES_BUCKET", "resumes")


def images_bucket() -> str:
    return os.getenv("IMAGES_BUCKET", "images")


def upload(bucket: str, filename: str, content: bytes, content_type: str) -> str:
    """Upload bytes to any bucket; return the public URL."""
    client = _get_client()
    key = f"{uuid4()}-{filename}"
    client.storage.from_(bucket).upload(
        path=key,
        file=content,
        file_options={"content-type": content_type},
    )
    return client.storage.from_(bucket).get_public_url(key)


def upload_resume(filename: str, content: bytes, content_type: str) -> str:
    return upload(resumes_bucket(), filename, content, content_type)


def upload_image(bucket: str, file: UploadFile) -> str:
    """Validate + upload an image. Returns the public URL.

    Used for candidate/employer profile pictures and the employer's company
    banner. Rejects non-image MIME types and files larger than 5 MB.
    """
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG, JPEG, or WebP images are supported.",
        )
    content = file.file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be 5 MB or smaller.",
        )
    return upload(
        bucket,
        file.filename or f"image-{uuid4()}",
        content,
        file.content_type,
    )


def download(file_url: str) -> bytes:
    """Fetch a previously-uploaded file by its public URL."""
    response = httpx.get(file_url, timeout=30.0)
    response.raise_for_status()
    return response.content
