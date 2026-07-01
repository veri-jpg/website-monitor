"""
Dependency FastAPI untuk autentikasi API key sederhana via header X-API-Key.

Kalau API_KEY di .env kosong (default), autentikasi dinonaktifkan — cocok
untuk development lokal. Di production, isi API_KEY dengan nilai acak yang kuat.
"""

import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    configured_key = settings.api_key
    if not configured_key:
        return  # auth dinonaktifkan kalau API_KEY kosong

    if not api_key or not secrets.compare_digest(api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key tidak valid atau tidak disertakan (header: X-API-Key)",
        )
