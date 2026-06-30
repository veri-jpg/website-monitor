"""
Model untuk tabel `check_results`.
Menyimpan histori setiap kali sistem melakukan pengecekan terhadap suatu website.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)

    status = Column(String, nullable=False)  # "success" atau "failed"
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)
    screenshot_path = Column(String, nullable=True)

    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    website = relationship("Website", back_populates="check_results")