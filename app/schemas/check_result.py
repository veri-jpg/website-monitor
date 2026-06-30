"""
Schema Pydantic untuk resource `CheckResult`.
Resource ini read-only dari sisi API - data hanya diisi otomatis
oleh scheduler/monitoring engine, bukan diinput manual oleh user.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CheckResultResponse(BaseModel):
    """Dipakai saat API mengembalikan histori hasil pengecekan."""
    id: int
    website_id: int
    status: str
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True