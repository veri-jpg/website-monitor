"""
Entry point utama aplikasi.
Menyatukan semua router dan menjalankan aplikasi FastAPI.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# FIX KHUSUS WINDOWS: uvicorn secara default memilih SelectorEventLoop di
# Windows, tapi event loop ini TIDAK MENDUKUNG subprocess - sementara
# Playwright WAJIB menjalankan Chromium sebagai subprocess. Tanpa baris ini,
# semua check_playwright() akan gagal dengan NotImplementedError saat
# dipanggil dari dalam proses FastAPI/uvicorn (walau berhasil jika dipanggil
# langsung lewat script python biasa).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# httpx mencatat setiap URL request di level INFO, termasuk URL Telegram Bot API
# yang mengandung token bot di path-nya. Naikkan ke WARNING supaya token tidak
# bocor ke log.
logging.getLogger("httpx").setLevel(logging.WARNING)

from app.api.routes_website import router as website_router
from app.api.routes_check_result import router as check_result_router
from app.api.routes_notification_rule import router as notification_rule_router
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler
from app.database import SessionLocal

# Import semua model di sini supaya SQLAlchemy mengenal seluruh relasi
# antar tabel sebelum aplikasi mulai menerima request.
from app.models.website import Website
from app.models.check_result import CheckResult
from app.models.notification_rule import NotificationRule

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # Reset flag is_checking yang mungkin tertinggal True akibat container
    # mati/restart di tengah siklus retry. Tanpa ini, website yang sedang
    # diproses saat crash tidak akan pernah dipolling lagi.
    db = SessionLocal()
    try:
        stuck = db.query(Website).filter(Website.is_checking == True).all()
        if stuck:
            logger.warning(
                f"Startup: mereset is_checking=True pada {len(stuck)} website "
                f"yang tertinggal dari sesi sebelumnya: {[w.id for w in stuck]}"
            )
            for w in stuck:
                w.is_checking = False
            db.commit()
    finally:
        db.close()

    start_scheduler()
    yield
    # --- SHUTDOWN ---
    shutdown_scheduler()


app = FastAPI(
    title="Universal Website Monitoring Platform",
    description="Platform monitoring website dengan dukungan HTTP check dan Playwright browser automation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(website_router)
app.include_router(check_result_router)
app.include_router(notification_rule_router)


@app.get("/")
def root():
    """Health check sederhana - memastikan aplikasi hidup."""
    return {"status": "ok", "message": "Website Monitoring Platform is running"}
