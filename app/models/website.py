"""
Model untuk tabel `websites`.
Menyimpan konfigurasi setiap website yang akan dimonitor.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    check_method = Column(String, nullable=False, default="http")
    interval_seconds = Column(Integer, nullable=False, default=300)
    selector = Column(String, nullable=True)
    credentials = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    is_checking = Column(Boolean, nullable=False, default=False)
    current_status = Column(String, nullable=True)  # "up", "down", atau None (belum pernah dicek)

    check_results = relationship(
        "CheckResult", back_populates="website", cascade="all, delete-orphan"
    )
    notification_rules = relationship(
        "NotificationRule", back_populates="website", cascade="all, delete-orphan"
    )