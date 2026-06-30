"""
Setup APScheduler - menjalankan run_due_checks() secara otomatis dan berkala,
sejak aplikasi FastAPI start sampai aplikasi dimatikan.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.jobs import run_due_checks

logger = logging.getLogger(__name__)

# Interval polling - seberapa sering scheduler "mengecek" apakah ada
# website yang sudah due untuk dicek. Ini BUKAN interval pengecekan
# website itu sendiri (itu diatur per-website lewat interval_seconds).
POLLING_INTERVAL_SECONDS = 10

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """Dipanggil sekali saat aplikasi FastAPI start."""
    scheduler.add_job(
        run_due_checks,
        trigger="interval",
        seconds=POLLING_INTERVAL_SECONDS,
        id="polling_check_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler dimulai - polling setiap {POLLING_INTERVAL_SECONDS} detik.")


def shutdown_scheduler() -> None:
    """Dipanggil sekali saat aplikasi FastAPI dimatikan."""
    scheduler.shutdown()
    logger.info("Scheduler dihentikan.")