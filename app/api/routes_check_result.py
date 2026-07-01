"""
Endpoint untuk resource `CheckResult`.
Read-only - data hanya diisi otomatis oleh scheduler, bukan oleh user.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_api_key
from app.database import get_db
from app.models.check_result import CheckResult
from app.schemas.check_result import CheckResultResponse

router = APIRouter(prefix="/check-results", tags=["check-results"], dependencies=[Depends(require_api_key)])


@router.get("/", response_model=List[CheckResultResponse])
def list_check_results(
    website_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Melihat histori hasil pengecekan.
    Bisa difilter berdasarkan website_id, dan dibatasi jumlahnya (default 50 terbaru).
    """
    query = db.query(CheckResult)
    if website_id is not None:
        query = query.filter(CheckResult.website_id == website_id)
    return query.order_by(CheckResult.checked_at.desc()).limit(limit).all()


@router.get("/{check_result_id}", response_model=CheckResultResponse)
def get_check_result(check_result_id: int, db: Session = Depends(get_db)):
    """Melihat detail satu hasil pengecekan berdasarkan id."""
    result = db.query(CheckResult).filter(CheckResult.id == check_result_id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Check result tidak ditemukan")
    return result