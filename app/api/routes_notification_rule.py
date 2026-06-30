"""
Endpoint CRUD untuk resource `NotificationRule`.
Menangani konfigurasi kemana notifikasi dikirim untuk suatu website.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification_rule import NotificationRule
from app.models.website import Website
from app.schemas.notification_rule import (
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
)

router = APIRouter(prefix="/notification-rules", tags=["notification-rules"])


@router.post("/", response_model=NotificationRuleResponse, status_code=201)
def create_notification_rule(payload: NotificationRuleCreate, db: Session = Depends(get_db)):
    """Menambah rule notifikasi baru untuk suatu website."""
    website = db.query(Website).filter(Website.id == payload.website_id).first()
    if website is None:
        raise HTTPException(status_code=404, detail="Website tidak ditemukan")

    new_rule = NotificationRule(**payload.model_dump())
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule


@router.get("/", response_model=List[NotificationRuleResponse])
def list_notification_rules(website_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Melihat daftar rule notifikasi, bisa difilter berdasarkan website_id."""
    query = db.query(NotificationRule)
    if website_id is not None:
        query = query.filter(NotificationRule.website_id == website_id)
    return query.all()


@router.get("/{rule_id}", response_model=NotificationRuleResponse)
def get_notification_rule(rule_id: int, db: Session = Depends(get_db)):
    """Melihat detail satu rule notifikasi."""
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule tidak ditemukan")
    return rule


@router.patch("/{rule_id}", response_model=NotificationRuleResponse)
def update_notification_rule(
    rule_id: int, payload: NotificationRuleUpdate, db: Session = Depends(get_db)
):
    """Mengubah sebagian data rule notifikasi."""
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule tidak ditemukan")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_notification_rule(rule_id: int, db: Session = Depends(get_db)):
    """Menghapus rule notifikasi."""
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule tidak ditemukan")

    db.delete(rule)
    db.commit()
    return None