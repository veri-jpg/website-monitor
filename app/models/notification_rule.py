"""
Model untuk tabel notification_rules.
Menyimpan konfigurasi kemana notifikasi dikirim untuk suatu website,
serta aturan retry sebelum notifikasi benar-benar dikirim.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)

    channel = Column(String, nullable=False)  # "telegram", "discord", atau "email"
    target = Column(String, nullable=False)   # chat_id / webhook_url / alamat email

    retry_count = Column(Integer, nullable=False, default=3)
    retry_delay_seconds = Column(Integer, nullable=False, default=30)

    website = relationship("Website", back_populates="notification_rules")