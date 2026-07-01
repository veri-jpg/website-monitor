"""
EncryptedJSON: SQLAlchemy TypeDecorator yang secara transparan mengenkripsi
dict ke string Fernet sebelum disimpan ke DB, dan mendekripsi saat dibaca.

Kolom di database bertipe TEXT (bukan JSON) — isinya ciphertext base64.
Calling code tidak perlu tahu ada enkripsi; cukup baca/tulis sebagai dict biasa.
"""

import json

from cryptography.fernet import Fernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


class EncryptedJSON(TypeDecorator):
    """Menyimpan dict Python sebagai ciphertext Fernet di kolom TEXT."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """dict → ciphertext string (saat INSERT/UPDATE)."""
        if value is None:
            return None
        plaintext = json.dumps(value, ensure_ascii=False).encode()
        return _get_fernet().encrypt(plaintext).decode()

    def process_result_value(self, value, dialect):
        """ciphertext string → dict (saat SELECT)."""
        if value is None:
            return None
        try:
            plaintext = _get_fernet().decrypt(value.encode())
            return json.loads(plaintext)
        except Exception:
            # Nilai tidak bisa didekripsi (plaintext lama atau key salah).
            # Kembalikan None supaya query tidak crash — credentials harus
            # di-set ulang via API.
            return None
