"""
Entry point utama aplikasi.
Menyatukan semua router dan menjalankan aplikasi FastAPI.
"""

import asyncio
import logging
import sys

# FIX KHUSUS WINDOWS: uvicorn secara default memilih SelectorEventLoop di
# Windows, tapi event loop ini TIDAK MENDUKUNG subprocess - sementara
# Playwright WAJIB menjalankan Chromium sebagai subprocess. Tanpa baris ini,
# semua check_playwright() akan gagal dengan NotImplementedError saat
# dipanggil dari dalam proses FastAPI/uvicorn (walau berhasil jika dipanggil
# langsung lewat script python biasa).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI

# Konfigurasi logging dasar - tanpa ini, logger.info(...) yang kita panggil
# di modul lain (scheduler, jobs) tidak akan tampil di konsol sama sekali.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

from app.api.routes_website import router as website_router
from app.api.routes_check_result import router as check_result_router
from app.api.routes_notification_rule import router as notification_rule_router
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler

# Import semua model di sini supaya SQLAlchemy mengenal seluruh relasi
# antar tabel sebelum aplikasi mulai menerima request.
# Tanpa ini, relationship() yang menunjuk model lain (misal "CheckResult")
# akan gagal dirangkai karena class-nya belum pernah "disentuh" aplikasi.
from app.models.website import Website
from app.models.check_result import CheckResult
from app.models.notification_rule import NotificationRule

app = FastAPI(
    title="Universal Website Monitoring Platform",
    description="Platform monitoring website dengan dukungan HTTP check dan Playwright browser automation.",
    version="0.1.0",
)

app.include_router(website_router)
app.include_router(check_result_router)
app.include_router(notification_rule_router)

@app.on_event("startup")
def on_startup():
    """Dipanggil otomatis sekali saat aplikasi FastAPI mulai berjalan."""
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    """Dipanggil otomatis sekali saat aplikasi FastAPI dimatikan."""
    shutdown_scheduler()


@app.get("/")
def root():
    """Health check sederhana - memastikan aplikasi hidup."""
    return {"status": "ok", "message": "Website Monitoring Platform is running"}