"""
Fixtures bersama untuk semua test.
Menyediakan SQLite in-memory database dan FastAPI TestClient yang
sudah di-override dependency get_db-nya supaya test tidak butuh PostgreSQL.
"""

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set env vars SEBELUM import app supaya pydantic-settings tidak error.
# Urutan penting: env harus ter-set sebelum modul app di-import pertama kali.
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("API_KEY", "")
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import app.database as app_database  # noqa: E402
import app.main as app_main  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Satu engine SQLite in-memory yang dipakai bersama oleh app dan test.
# StaticPool menjaga koneksi yang sama tetap hidup sehingga tabel yang
# dibuat lewat create_all tetap terlihat oleh semua session.
_TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override engine dan SessionLocal milik app supaya lifespan dan semua
# kode yang memanggil SessionLocal() juga memakai DB test yang sama.
# Harus patch keduanya: modul database (untuk kode yang import module-nya)
# dan main (karena `from app.database import SessionLocal` membuat binding lokal
# di main.py yang tidak ter-update kalau hanya database.SessionLocal yang diganti).
app_database.engine = engine
app_database.SessionLocal = TestingSessionLocal
app_main.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Mock scheduler supaya background job tidak jalan selama test.
    with patch("app.main.start_scheduler"), patch("app.main.shutdown_scheduler"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
