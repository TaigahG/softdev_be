"""Supabase JWT verification and FastAPI dependencies.

Verifies tokens against Supabase's JWKS endpoint (ES256 / RS256 asymmetric
crypto, the modern signing-keys mechanism). The public key is fetched once
from the project's /.well-known/jwks.json and cached by PyJWKClient.

Exposes three dependencies:

    get_current_user      → AuthUser (UUID + email + metadata)
    get_current_candidate → Candidate row (404 if profile missing)
    get_current_employer  → Employer row (404 if profile missing)

Profile rows are guaranteed to exist (created by the auth.users trigger),
but we still 404 if the user signed up with the wrong role.
"""
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Employer


_bearer = HTTPBearer(auto_error=True)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        if not supabase_url:
            raise RuntimeError("SUPABASE_URL is not set in .env")
        _jwks_client = PyJWKClient(
            f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        )
    return _jwks_client


@dataclass
class AuthUser:
    user_id: UUID
    email: str | None
    metadata: dict[str, Any]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthUser:
    token = credentials.credentials
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid token: {e}"
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token missing sub claim",
        )

    return AuthUser(
        user_id=UUID(sub),
        email=payload.get("email"),
        metadata=payload.get("user_metadata") or {},
    )


def get_current_candidate(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Candidate:
    candidate = (
        db.query(Candidate).filter(Candidate.user_id == user.user_id).first()
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="candidate profile not found for this user",
        )
    return candidate


def get_current_employer(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Employer:
    employer = db.query(Employer).filter(Employer.user_id == user.user_id).first()
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="employer profile not found for this user",
        )
    return employer
