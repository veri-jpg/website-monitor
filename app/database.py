"""
File ini menyiapkan koneksi ke PostgreSQL menggunakan SQLAlchemy.

Konsep penting yang perlu dipahami:
- `engine`     : objek yang tahu cara konek ke database (alamat, kredensial)
- `SessionLocal`: "pabrik" yang membuat session baru setiap kali dibutuhkan.
                  Satu session = satu unit kerja (misal: satu request API).
- `Base`       : kelas dasar yang nanti diturunkan oleh semua model
                  (Website, CheckResult, dst) supaya SQLAlchemy tahu
                  mereka adalah tabel database.
- `get_db()`   : dependency yang dipakai FastAPI untuk membuka session
                  di awal request dan menutupnya otomatis setelah selesai,
                  supaya tidak ada koneksi yang "menggantung".
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency untuk endpoint FastAPI.
    Contoh pakai di endpoint:

        @router.get("/websites")
        def list_websites(db: Session = Depends(get_db)):
            return db.query(Website).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
