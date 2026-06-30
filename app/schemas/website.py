"""
Schema Pydantic untuk resource `Website`.
Mengatur validasi data masuk (request) dan kontrol data keluar (response)
pada endpoint API, terpisah dari struktur tabel database di models/website.py.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WebsiteBase(BaseModel):
    """Field yang umum dipakai di Create dan Response, biar tidak duplikat tulisan."""
    name: str
    url: str
    check_method: str = "http"
    interval_seconds: int = 300
    selector: Optional[str] = None
    is_active: bool = True


class WebsiteCreate(WebsiteBase):
    """
    Dipakai saat user membuat website baru lewat POST /websites.
    Semua field di WebsiteBase wajib (kecuali yang sudah ada default-nya),
    ditambah credentials yang opsional kalau memang dibutuhkan.
    """
    credentials: Optional[dict] = None


class WebsiteUpdate(BaseModel):
    """
    Dipakai saat user update sebagian data lewat PATCH /websites/{id}.
    Semua field opsional - cuma field yang dikirim yang akan diupdate.
    """
    name: Optional[str] = None
    url: Optional[str] = None
    check_method: Optional[str] = None
    interval_seconds: Optional[int] = None
    selector: Optional[str] = None
    credentials: Optional[dict] = None
    is_active: Optional[bool] = None


class WebsiteResponse(WebsiteBase):
    """
    Dipakai saat API mengembalikan data ke user.
    Sengaja TIDAK menyertakan field `credentials` - data sensitif itu
    tidak pernah dikirim balik lewat response API.
    """
    id: int
    created_at: datetime

    class Config:
        from_attributes = True