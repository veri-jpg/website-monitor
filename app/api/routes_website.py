"""
Endpoint CRUD untuk resource `Website`.
Menangani: tambah, lihat daftar, lihat detail, ubah, dan hapus website yang dimonitor.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.website import Website
from app.models.check_result import CheckResult
from app.schemas.website import WebsiteCreate, WebsiteUpdate, WebsiteResponse
from app.schemas.check_result import CheckResultResponse
from app.monitors.http_checker import check_http
from app.monitors.playwright_checker import check_playwright

router = APIRouter(prefix="/websites", tags=["websites"])


@router.post("/", response_model=WebsiteResponse, status_code=201)
def create_website(payload: WebsiteCreate, db: Session = Depends(get_db)):
    """Menambah website baru untuk dimonitor."""
    new_website = Website(**payload.model_dump())
    db.add(new_website)
    db.commit()
    db.refresh(new_website)
    return new_website


@router.get("/", response_model=List[WebsiteResponse])
def list_websites(db: Session = Depends(get_db)):
    """Melihat daftar seluruh website yang dimonitor."""
    return db.query(Website).all()


@router.get("/{website_id}", response_model=WebsiteResponse)
def get_website(website_id: int, db: Session = Depends(get_db)):
    """Melihat detail satu website berdasarkan id."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if website is None:
        raise HTTPException(status_code=404, detail="Website tidak ditemukan")
    return website


@router.patch("/{website_id}", response_model=WebsiteResponse)
def update_website(website_id: int, payload: WebsiteUpdate, db: Session = Depends(get_db)):
    """Mengubah sebagian data website. Hanya field yang dikirim yang diupdate."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if website is None:
        raise HTTPException(status_code=404, detail="Website tidak ditemukan")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(website, field, value)

    db.commit()
    db.refresh(website)
    return website


@router.delete("/{website_id}", status_code=204)
def delete_website(website_id: int, db: Session = Depends(get_db)):
    """Menghapus website dari daftar monitoring."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if website is None:
        raise HTTPException(status_code=404, detail="Website tidak ditemukan")

    db.delete(website)
    db.commit()
    return None


@router.post("/{website_id}/check-now", response_model=CheckResultResponse)
async def trigger_check_now(website_id: int, db: Session = Depends(get_db)):
    """
    Memicu pengecekan SEKARANG secara manual (tanpa menunggu scheduler).
    Mendukung check_method "http" dan "playwright".
    Hasilnya langsung disimpan sebagai baris baru di tabel check_results.
    """
    website = db.query(Website).filter(Website.id == website_id).first()
    if website is None:
        raise HTTPException(status_code=404, detail="Website tidak ditemukan")

    if website.check_method == "playwright":
        result = await check_playwright(
            website.url, selector=website.selector, credentials=website.credentials
        )
    elif website.check_method == "http":
        result = await check_http(website.url)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"check_method '{website.check_method}' tidak dikenali",
        )

    new_check_result = CheckResult(website_id=website.id, **result)
    db.add(new_check_result)
    db.commit()
    db.refresh(new_check_result)
    return new_check_result