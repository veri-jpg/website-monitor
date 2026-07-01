"""
Scheduler job - dijalankan secara berkala oleh APScheduler.
Bertugas mencari website yang sudah waktunya dicek ulang, MELEPAS proses
pengecekan (dengan retry mechanism) ke background sebagai task independen,
lalu segera kembali tanpa menunggu - supaya putaran polling berikutnya
tidak ikut tertunda oleh website yang masih dalam siklus retry panjang.

Mendukung dua check_method: "http" (via HTTPX) dan "playwright" (via
browser automation) - keduanya dipanggil lewat fungsi yang sama
(_run_single_check) supaya logic retry dan notifikasi tetap seragam.

Notifikasi dikirim secara EDGE-TRIGGERED - hanya saat status website
BERUBAH (up->down atau down->up), bukan setiap kali polling menemukan
website itu masih down. Ini mencegah spam notifikasi berulang untuk
downtime yang sama.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import SessionLocal
from app.models.website import Website
from app.models.check_result import CheckResult
from app.models.notification_rule import NotificationRule
from app.monitors.http_checker import check_http
from app.monitors.playwright_checker import check_playwright
from app.notifiers.telegram import send_telegram_notification
from app.notifiers.discord import send_discord_notification
from app.notifiers.email import send_email_notification

logger = logging.getLogger(__name__)

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY_SECONDS = 30


def _is_due_for_check(website: Website, now: datetime) -> bool:
    """
    Menentukan apakah sebuah website sudah waktunya dicek lagi.
    Website yang sedang diproses (is_checking=True) TIDAK PERNAH due,
    supaya tidak ada dua siklus retry berjalan bersamaan untuk website yang sama.
    """
    if website.is_checking:
        return False

    last_checked = website.last_checked_at
    if last_checked is None:
        return True

    if last_checked.tzinfo is None:
        last_checked = last_checked.replace(tzinfo=timezone.utc)

    next_due_time = last_checked + timedelta(seconds=website.interval_seconds)
    return now >= next_due_time


def _get_retry_config(website: Website) -> tuple[int, int]:
    rule = website.notification_rules[0] if website.notification_rules else None
    if rule is None:
        return DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS
    return rule.retry_count, rule.retry_delay_seconds


async def _run_single_check(
    check_method: str, url: str, selector: Optional[str], credentials: Optional[dict]
) -> dict:
    """
    Titik tunggal pemanggilan monitoring engine yang sesuai check_method.
    Kalau nanti ada engine baru (misal API GraphQL khusus), cukup tambah
    cabang di sini tanpa mengubah logic retry/scheduler yang sudah ada.
    """
    if check_method == "playwright":
        return await check_playwright(url, selector=selector, credentials=credentials)
    return await check_http(url)


async def _check_with_retry(
    website_id: int,
    check_method: str,
    url: str,
    selector: Optional[str],
    credentials: Optional[dict],
    retry_count: int,
    retry_delay_seconds: int,
) -> list[dict]:
    """
    Siklus retry murni - tidak menyentuh database session sama sekali.
    """
    all_attempts = []

    for attempt_number in range(1, retry_count + 2):
        result = await _run_single_check(check_method, url, selector, credentials)
        all_attempts.append(result)

        if result["status"] == "success":
            logger.info(f"  -> website_id={website_id}: sukses pada percobaan ke-{attempt_number}")
            return all_attempts

        is_last_attempt = attempt_number == retry_count + 1
        if is_last_attempt:
            logger.warning(
                f"  -> website_id={website_id}: GAGAL setelah {attempt_number} percobaan"
            )
            return all_attempts

        logger.info(
            f"  -> website_id={website_id}: percobaan ke-{attempt_number} gagal, "
            f"retry dalam {retry_delay_seconds} detik..."
        )
        await asyncio.sleep(retry_delay_seconds)

    return all_attempts


async def _dispatch_notification(channel: str, target: str, message: str) -> None:
    if channel == "telegram":
        await send_telegram_notification(target, message)
    elif channel == "email":
        await send_email_notification(target, message)
    elif channel == "discord":
        await send_discord_notification(target, message)
    else:
        logger.warning(f"Channel notifikasi '{channel}' belum didukung - notifikasi dilewati.")


async def _handle_status_transition(db, website: Website, final_status: str) -> None:
    """
    Inti dari edge-triggered notification.
    """
    previous_status = website.current_status

    if previous_status == final_status:
        return

    website.current_status = final_status

    rules = website.notification_rules
    if not rules:
        logger.info(
            f"  -> {website.name}: status berubah jadi '{final_status}', "
            f"tapi belum ada NotificationRule terpasang - notifikasi dilewati."
        )
        return

    if final_status == "down":
        message = f"Website '{website.name}' TERDETEKSI DOWN setelah semua retry gagal."
    else:
        message = f"Website '{website.name}' sudah PULIH dan kembali normal."

    for rule in rules:
        await _dispatch_notification(rule.channel, rule.target, message)


async def _process_website_in_background(
    website_id: int,
    check_method: str,
    url: str,
    selector: Optional[str],
    credentials: Optional[dict],
    retry_count: int,
    retry_delay_seconds: int,
) -> None:
    """
    Wrapper yang dijalankan sebagai background task (lewat asyncio.create_task).
    """
    attempts = await _check_with_retry(
        website_id, check_method, url, selector, credentials, retry_count, retry_delay_seconds
    )
    final_status = "up" if attempts[-1]["status"] == "success" else "down"

    db = SessionLocal()
    try:
        for attempt_result in attempts:
            db.add(CheckResult(website_id=website_id, **attempt_result))

        website = db.query(Website).filter(Website.id == website_id).first()
        if website:
            website.last_checked_at = datetime.now(timezone.utc)
            website.is_checking = False
            await _handle_status_transition(db, website, final_status)

        db.commit()
    except Exception:
        logger.exception(f"Error saat menyimpan hasil background check untuk website_id={website_id}")
        db.rollback()
    finally:
        db.close()


async def run_due_checks() -> None:
    """
    Satu "putaran" polling: cari website yang due (HTTP maupun Playwright),
    tandai sebagai "sedang diproses", lepas ke background, lalu segera selesai.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        active_websites = (
            db.query(Website)
            .filter(
                Website.is_active == True,
                Website.check_method.in_(["http", "playwright"]),
            )
            .all()
        )
        due_websites = [w for w in active_websites if _is_due_for_check(w, now)]

        if not due_websites:
            logger.info("Polling: tidak ada website yang due untuk dicek saat ini.")
            return

        logger.info(f"Polling: {len(due_websites)} website due untuk dicek, melepas ke background.")

        for website in due_websites:
            retry_count, retry_delay_seconds = _get_retry_config(website)
            website.is_checking = True

            asyncio.create_task(
                _process_website_in_background(
                    website.id,
                    website.check_method,
                    website.url,
                    website.selector,
                    website.credentials,
                    retry_count,
                    retry_delay_seconds,
                )
            )

        db.commit()

    except Exception:
        logger.exception("Terjadi error tak terduga saat menjalankan polling check.")
        db.rollback()
    finally:
        db.close()