"""encrypt credentials column

Revision ID: f3c1a9d72e05
Revises: aaec7de223cc
Create Date: 2026-07-01 00:00:00.000000

Mengubah kolom `credentials` dari JSON ke TEXT dan mengenkripsi
semua nilai yang sudah ada menggunakan Fernet (ENCRYPTION_KEY dari env).
"""
from __future__ import annotations

import json
import os

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet

revision = "f3c1a9d72e05"
down_revision = "aaec7de223cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Baca semua credentials yang masih berupa JSON (plaintext) sebelum
    #    tipe kolom diubah - psycopg2 mengembalikan dict Python untuk kolom JSON.
    rows = conn.execute(
        sa.text("SELECT id, credentials FROM websites WHERE credentials IS NOT NULL")
    ).fetchall()

    # 2. Ubah tipe kolom dari JSON ke TEXT.
    #    postgresql_using meng-cast JSON ke representasi string-nya.
    op.alter_column(
        "websites",
        "credentials",
        type_=sa.Text(),
        postgresql_using="credentials::text",
        existing_nullable=True,
    )

    # 3. Enkripsi data lama yang baru saja di-cast ke TEXT.
    if rows:
        key = os.environ.get("ENCRYPTION_KEY", "").strip().strip('"').strip("'")
        if not key:
            raise RuntimeError("ENCRYPTION_KEY environment variable tidak ditemukan.")
        fernet = Fernet(key.encode())
        for row_id, cred in rows:
            if cred is None:
                continue
            # Setelah ALTER TYPE, kolom sudah TEXT, tapi data di `rows` masih
            # berupa dict Python (diambil sebelum ALTER). Kita enkripsi dict-nya.
            if isinstance(cred, str):
                try:
                    cred = json.loads(cred)
                except json.JSONDecodeError:
                    continue  # sudah terenkripsi atau malformed, lewati
            encrypted = fernet.encrypt(
                json.dumps(cred, ensure_ascii=False).encode()
            ).decode()
            conn.execute(
                sa.text("UPDATE websites SET credentials = :enc WHERE id = :id"),
                {"enc": encrypted, "id": row_id},
            )


def downgrade() -> None:
    # Downgrade: ubah kembali ke JSON; nilai yang sudah terenkripsi menjadi
    # ciphertext string di kolom JSON (tidak ada dekripsi otomatis saat downgrade).
    op.alter_column(
        "websites",
        "credentials",
        type_=sa.JSON(),
        postgresql_using="credentials::json",
        existing_nullable=True,
    )
