"""
Schema Pydantic untuk resource `NotificationRule`.
Mengatur validasi data masuk dan kontrol data keluar untuk konfigurasi
kemana notifikasi dikirim ketika sebuah website bermasalah.
"""

from typing import Optional

from pydantic import BaseModel


class NotificationRuleBase(BaseModel):
    channel: str          # "telegram", "discord", atau "email"
    target: str           # chat_id / webhook_url / alamat email
    retry_count: int = 3
    retry_delay_seconds: int = 30


class NotificationRuleCreate(NotificationRuleBase):
    """Dipakai saat user menambah rule notifikasi baru untuk suatu website."""
    website_id: int


class NotificationRuleUpdate(BaseModel):
    """Semua field opsional - dipakai untuk update sebagian data."""
    channel: Optional[str] = None
    target: Optional[str] = None
    retry_count: Optional[int] = None
    retry_delay_seconds: Optional[int] = None


class NotificationRuleResponse(NotificationRuleBase):
    id: int
    website_id: int

    class Config:
        from_attributes = True